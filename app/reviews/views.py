from flask import Blueprint, request, session, current_app
from app.utils.db import get_db_connection
from app.utils.response import success, fail
from app.utils.auth import login_required, role_required
from config import get_config
import json
from datetime import datetime

config = get_config()
ROLES = config.ROLES

reviews_bp = Blueprint('reviews', __name__, url_prefix='/api/reviews')

# 评分标准配置
SCORING_CRITERIA = {
    '自然科学类学术论文': [
        {'key': 'scientific', 'label': '科学性', 'max': 40, 'desc': '研究方法、数据可靠、论证严谨'},
        {'key': 'innovation', 'label': '创新性', 'max': 30, 'desc': '创新点、学术价值'},
        {'key': 'value', 'label': '应用价值', 'max': 30, 'desc': '现实意义、应用前景'}
    ],
    '哲学社会科学类社会调查报告': [
        {'key': 'scientific', 'label': '科学性', 'max': 40, 'desc': '调查方法、数据真实'},
        {'key': 'innovation', 'label': '创新性', 'max': 30, 'desc': '视角新颖、见解独特'},
        {'key': 'value', 'label': '应用价值', 'max': 30, 'desc': '问题导向、对策建议'}
    ],
    '科技发明制作': [
        {'key': 'scientific', 'label': '科学性', 'max': 40, 'desc': '技术原理、实现方法'},
        {'key': 'innovation', 'label': '创新性', 'max': 30, 'desc': '技术创新、突破性'},
        {'key': 'value', 'label': '应用价值', 'max': 30, 'desc': '实用性、推广前景'}
    ]
}

def check_reviewer_conflict(conn, reviewer_id, project_id):
    """
    检查评委与项目是否存在利益冲突
    """
    reviewer = conn.execute('SELECT * FROM users WHERE id = ?', (reviewer_id,)).fetchone()
    project = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    
    if not reviewer or not project:
        return None
        
    # 1. 评委是项目的指导教师
    if project['advisor_name'] == reviewer['real_name']:
        return "评委是项目的指导教师"
        
    # 2. 评委与项目负责人/成员同学院且同部门 (简单模拟同教研室)
    members = conn.execute('SELECT * FROM project_members WHERE project_id = ?', (project_id,)).fetchall()
    for m in members:
        # 这里需要更复杂的逻辑来判断同教研室，目前简单判断同学院同部门
        if reviewer['college'] == project['college'] and reviewer['department'] == project['department']:
            return "评委与项目团队属于同一教研室/部门"
            
    return None

@reviews_bp.route('/tasks', methods=['GET'])
@login_required
def get_my_tasks():
    user_id = session.get('user_id')
    conn = get_db_connection()
    tasks = conn.execute('''
        SELECT t.*, p.title as project_title, p.status as project_status, p.project_type, p.competition_id, p.college as project_college,
               p.extra_info as project_extra_info
        FROM review_tasks t
        JOIN projects p ON t.project_id = p.id
        WHERE t.judge_id = ?
        ORDER BY t.created_at DESC
    ''', (user_id,)).fetchall()
    
    result = []
    for t in tasks:
        task_dict = dict(t)
        
        # 盲评逻辑：对于大挑项目，隐藏敏感信息
        # 假设通过 competition_id 或 project_type 识别
        is_blind = str(task_dict.get('review_level') or '').strip() == 'school'
        if is_blind:
            task_dict['project_college'] = ''
            extra_raw = task_dict.get('project_extra_info') or ''
            extra_obj = {}
            try:
                extra_obj = json.loads(extra_raw or '{}')
            except Exception:
                extra_obj = {}
            safe_extra = {}
            if isinstance(extra_obj, dict):
                for k in ['作品类别', 'discipline_group', '学科类别', '组别']:
                    if k in extra_obj:
                        safe_extra[k] = extra_obj.get(k)
            task_dict['project_extra_info'] = json.dumps(safe_extra, ensure_ascii=False)
            
        # 获取作品类别以匹配评分项
        extra = {}
        try:
            extra = json.loads(task_dict.get('project_extra_info') or '{}')
        except:
            pass
            
        category = extra.get('作品类别', '自然科学类学术论文')
        task_dict['scoring_criteria'] = SCORING_CRITERIA.get(category, SCORING_CRITERIA['自然科学类学术论文'])
        
        # Fetch scores if any
        scores = conn.execute('SELECT * FROM review_scores WHERE task_id = ?', (t['id'],)).fetchall()
        task_dict['criteria_scores'] = {s['criteria']: s['score'] for s in scores}
        
        # Fetch score details (reasons) from JSON if exists
        try:
            task_dict['score_details'] = json.loads(t['score_details'] or '{}')
        except:
            task_dict['score_details'] = {}
            
        result.append(task_dict)
        
    return success(data=result)

def _normalize_scope_key_for_college(s):
    s = (s or '').strip()
    if not s:
        return ''
    return s.split('（')[0].split('(')[0].strip()

def normalize_review_award(v):
    s = str(v or '').strip()
    if not s:
        return 'none'
    low = s.lower()
    if low in ['none', '无']:
        return 'none'
    if low in ['excellent', '优秀', '优秀奖']:
        return 'excellent'
    if low in ['special', '特等奖', '特等']:
        return 'special'
    if low in ['first', '一等奖', '一等']:
        return 'first'
    if low in ['second', '二等奖', '二等']:
        return 'second'
    if low in ['third', '三等奖', '三等']:
        return 'third'
    return 'none'

@reviews_bp.route('/awards/set', methods=['POST'])
@login_required
@role_required([ROLES['COLLEGE_APPROVER'], ROLES['SCHOOL_APPROVER'], ROLES['PROJECT_ADMIN'], ROLES['SYSTEM_ADMIN']])
def set_review_awards():
    user_id = session.get('user_id')
    role = session.get('role')
    data = request.json or {}
    review_level = str(data.get('review_level') or '').strip()
    award = normalize_review_award(data.get('award'))
    project_ids = data.get('project_ids') or []

    if review_level not in ['college', 'school']:
        return fail('review_level 非法', 400)
    if not isinstance(project_ids, list) or not project_ids:
        return fail('请选择项目', 400)

    if review_level == 'college' and role not in [ROLES['COLLEGE_APPROVER'], ROLES['PROJECT_ADMIN'], ROLES['SYSTEM_ADMIN']]:
        return fail('无权限', 403)
    if review_level == 'school' and role not in [ROLES['SCHOOL_APPROVER'], ROLES['PROJECT_ADMIN'], ROLES['SYSTEM_ADMIN']]:
        return fail('无权限', 403)

    award_field = 'college_award' if review_level == 'college' else 'school_award'
    score_field = 'college_avg_score' if review_level == 'college' else 'school_avg_score'
    rank_field = 'college_rank' if review_level == 'college' else 'school_rank'

    ids = []
    for x in project_ids:
        try:
            ids.append(int(x))
        except Exception:
            continue
    ids = [i for i in ids if i > 0]
    if not ids:
        return fail('请选择项目', 400)

    conn = get_db_connection()
    placeholders = ','.join(['?'] * len(ids))
    rows = conn.execute(
        f'''
        SELECT id, college, competition_id, {score_field} as avg_score, {rank_field} as rank_no
        FROM projects
        WHERE id IN ({placeholders})
        ''',
        ids
    ).fetchall()
    if not rows:
        return fail('项目不存在', 404)

    if role == ROLES['COLLEGE_APPROVER'] and review_level == 'college':
        my_college = _normalize_scope_key_for_college(session.get('college', ''))
        for r in rows:
            if _normalize_scope_key_for_college(str(r['college'] or '')) != my_college:
                return fail('无权限', 403)

    missing = []
    for r in rows:
        try:
            avg_ok = r['avg_score'] is not None
            rank_ok = int(r['rank_no'] or 0) > 0
        except Exception:
            avg_ok = False
            rank_ok = False
        if not (avg_ok and rank_ok):
            missing.append(int(r['id']))
    if missing:
        return fail('请先完成评审并计算平均分/排名后再评奖', 400, data={'sample_project_ids': missing[:10]})

    try:
        conn.execute('BEGIN TRANSACTION')
        for pid in [int(r['id']) for r in rows]:
            conn.execute(f'UPDATE projects SET {award_field} = ? WHERE id = ?', (award, pid))
        try:
            conn.execute(
                'INSERT INTO system_logs (user_id, action, details, ip_address) VALUES (?, ?, ?, ?)',
                (user_id, 'SET_REVIEW_AWARDS', json.dumps({'review_level': review_level, 'award': award, 'project_ids': ids}, ensure_ascii=False), request.remote_addr)
            )
        except Exception:
            pass
        conn.execute('COMMIT')
        return success(message='已设置奖项')
    except Exception as e:
        try:
            conn.execute('ROLLBACK')
        except Exception:
            pass
        return fail(str(e), 500)

def _recalc_review_ranks(conn, competition_id, review_level):
    review_level = str(review_level or '').strip()
    if review_level not in ['college', 'school']:
        return
    try:
        competition_id = int(competition_id)
    except Exception:
        return

    score_field = f'{review_level}_avg_score'
    rank_field = f'{review_level}_rank'
    conn.execute(f'UPDATE projects SET {rank_field} = NULL WHERE competition_id = ?', (competition_id,))

    if review_level == 'college':
        rows = conn.execute(
            f'''
            SELECT id, {score_field} as score, college
            FROM projects
            WHERE competition_id = ?
              AND id IN (SELECT DISTINCT project_id FROM review_tasks WHERE review_level = ?)
              AND {score_field} IS NOT NULL
            ''',
            (competition_id, review_level)
        ).fetchall()
        rows = [dict(r) for r in (rows or [])]
        grouped = {}
        for r in rows:
            key = _normalize_scope_key_for_college(str(r.get('college') or ''))
            grouped.setdefault(key, []).append(r)
        for _, items in grouped.items():
            items.sort(key=lambda x: (float(x.get('score') or 0), -int(x.get('id') or 0)), reverse=True)
            rank = 1
            for p in items:
                conn.execute(f'UPDATE projects SET {rank_field} = ? WHERE id = ?', (rank, int(p['id'])))
                rank += 1
        return

    rows = conn.execute(
        f'''
        SELECT id, {score_field} as score, extra_info
        FROM projects
        WHERE competition_id = ?
          AND id IN (SELECT DISTINCT project_id FROM review_tasks WHERE review_level = ?)
          AND {score_field} IS NOT NULL
        ''',
        (competition_id, review_level)
    ).fetchall()
    rows = [dict(r) for r in (rows or [])]
    grouped = {}
    for r in rows:
        dg = ''
        try:
            extra = json.loads(r.get('extra_info') or '{}')
            if isinstance(extra, dict):
                dg = str(extra.get('discipline_group') or extra.get('学科类别') or extra.get('组别') or '')
        except Exception:
            dg = ''
        key = dg or 'all'
        grouped.setdefault(key, []).append(r)
    for _, items in grouped.items():
        items.sort(key=lambda x: (float(x.get('score') or 0), -int(x.get('id') or 0)), reverse=True)
        rank = 1
        for p in items:
            conn.execute(f'UPDATE projects SET {rank_field} = ? WHERE id = ?', (rank, int(p['id'])))
            rank += 1

def _load_promotion_rule(conn, competition_id, review_level, scope_key):
    row = conn.execute(
        'SELECT rule_type, rule_value FROM review_promotion_rules WHERE competition_id = ? AND review_level = ? AND scope_key = ?',
        (int(competition_id), str(review_level), str(scope_key or ''))
    ).fetchone()
    if not row:
        return None
    try:
        return {'rule_type': str(row['rule_type']), 'rule_value': float(row['rule_value'])}
    except Exception:
        return None

def _upsert_promotion_rule(conn, competition_id, review_level, scope_key, rule_type, rule_value, updated_by):
    existing = conn.execute(
        'SELECT id FROM review_promotion_rules WHERE competition_id = ? AND review_level = ? AND scope_key = ?',
        (int(competition_id), str(review_level), str(scope_key or ''))
    ).fetchone()
    if existing:
        conn.execute(
            'UPDATE review_promotion_rules SET rule_type = ?, rule_value = ?, updated_by = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (str(rule_type), float(rule_value), int(updated_by) if updated_by else None, int(existing['id']))
        )
        return int(existing['id'])
    conn.execute(
        '''
        INSERT INTO review_promotion_rules (competition_id, review_level, scope_key, rule_type, rule_value, updated_by)
        VALUES (?, ?, ?, ?, ?, ?)
        ''',
        (int(competition_id), str(review_level), str(scope_key or ''), str(rule_type), float(rule_value), int(updated_by) if updated_by else None)
    )
    return int(conn.execute('SELECT last_insert_rowid() as id').fetchone()['id'])

@reviews_bp.route('/promotion_rule', methods=['GET'])
@login_required
@role_required([ROLES['COLLEGE_APPROVER'], ROLES['SCHOOL_APPROVER'], ROLES['PROJECT_ADMIN'], ROLES['SYSTEM_ADMIN']])
def get_promotion_rule():
    competition_id = request.args.get('competition_id')
    review_level = (request.args.get('review_level') or 'college').strip()
    if not competition_id:
        return fail('缺少 competition_id', 400)
    if review_level not in ['college', 'school']:
        return fail('review_level 非法', 400)

    role = session.get('role')
    scope_key = (request.args.get('scope_key') or '').strip()
    if review_level == 'college':
        if role == ROLES['COLLEGE_APPROVER']:
            scope_key = _normalize_scope_key_for_college(session.get('college', ''))
        else:
            scope_key = _normalize_scope_key_for_college(scope_key)
    else:
        scope_key = scope_key or (request.args.get('discipline_group') or 'all')

    conn = get_db_connection()
    rule = _load_promotion_rule(conn, competition_id, review_level, scope_key)
    if not rule:
        return success(data={'competition_id': int(competition_id), 'review_level': review_level, 'scope_key': scope_key, 'rule_type': '', 'rule_value': 0, 'exists': False})
    return success(data={'competition_id': int(competition_id), 'review_level': review_level, 'scope_key': scope_key, 'rule_type': rule['rule_type'], 'rule_value': rule['rule_value'], 'exists': True})

@reviews_bp.route('/promotion_rule', methods=['PUT'])
@login_required
@role_required([ROLES['COLLEGE_APPROVER'], ROLES['SCHOOL_APPROVER'], ROLES['PROJECT_ADMIN'], ROLES['SYSTEM_ADMIN']])
def set_promotion_rule():
    data = request.json or {}
    competition_id = data.get('competition_id')
    review_level = str(data.get('review_level') or 'college').strip()
    rule_type = str(data.get('rule_type') or '').strip()
    rule_value = data.get('rule_value')
    if not competition_id:
        return fail('缺少 competition_id', 400)
    if review_level not in ['college', 'school']:
        return fail('review_level 非法', 400)
    if rule_type not in ['count', 'percent']:
        return fail('rule_type 非法', 400)
    try:
        rule_value = float(rule_value)
    except Exception:
        return fail('rule_value 非法', 400)
    if rule_value <= 0:
        return fail('rule_value 必须大于 0', 400)
    if rule_type == 'percent' and rule_value > 100:
        return fail('percent 不能大于 100', 400)

    role = session.get('role')
    scope_key = str(data.get('scope_key') or '').strip()
    if review_level == 'college':
        if role == ROLES['COLLEGE_APPROVER']:
            scope_key = _normalize_scope_key_for_college(session.get('college', ''))
        else:
            scope_key = _normalize_scope_key_for_college(scope_key)
    else:
        scope_key = scope_key or (data.get('discipline_group') or 'all')

    if role == ROLES['COLLEGE_APPROVER'] and review_level != 'college':
        return fail('无权限设置该级别规则', 403)
    if role == ROLES['SCHOOL_APPROVER'] and review_level != 'school':
        return fail('无权限设置该级别规则', 403)

    conn = get_db_connection()
    try:
        conn.execute('BEGIN TRANSACTION')
        rid = _upsert_promotion_rule(conn, competition_id, review_level, scope_key, rule_type, rule_value, session.get('user_id'))
        conn.execute('COMMIT')
        return success(data={'id': rid}, message='保存成功')
    except Exception as e:
        try:
            conn.execute('ROLLBACK')
        except Exception:
            pass
        return fail(str(e), 500)

@reviews_bp.route('/publish', methods=['POST'])
@login_required
@role_required([ROLES['COLLEGE_APPROVER'], ROLES['SCHOOL_APPROVER'], ROLES['PROJECT_ADMIN'], ROLES['SYSTEM_ADMIN']])
def publish_results():
    import math
    data = request.json or {}
    competition_id = data.get('competition_id')
    review_level = str(data.get('review_level') or 'college').strip()
    if not competition_id:
        return fail('缺少 competition_id', 400)
    if review_level not in ['college', 'school']:
        return fail('review_level 非法', 400)

    role = session.get('role')
    if role == ROLES['COLLEGE_APPROVER'] and review_level != 'college':
        return fail('无权限发布该级别结果', 403)
    if role == ROLES['SCHOOL_APPROVER'] and review_level != 'school':
        return fail('无权限发布该级别结果', 403)

    scope_key = str(data.get('scope_key') or '').strip()
    if review_level == 'college':
        if role == ROLES['COLLEGE_APPROVER']:
            scope_key = _normalize_scope_key_for_college(session.get('college', ''))
        else:
            scope_key = _normalize_scope_key_for_college(scope_key)
    else:
        scope_key = scope_key or (data.get('discipline_group') or 'all')

    conn = get_db_connection()
    rule_type = (data.get('rule_type') or '').strip()
    rule_value = data.get('rule_value')
    if not rule_type:
        rule = _load_promotion_rule(conn, competition_id, review_level, scope_key)
        if not rule:
            return fail('未配置晋级规则', 400)
        rule_type = rule['rule_type']
        rule_value = rule['rule_value']
    else:
        if rule_type not in ['count', 'percent']:
            return fail('rule_type 非法', 400)
        try:
            rule_value = float(rule_value)
        except Exception:
            return fail('rule_value 非法', 400)

    score_field = f'{review_level}_avg_score'
    rank_field = f'{review_level}_rank'
    award_field = 'college_award' if review_level == 'college' else 'school_award'
    lock_field = 'college_result_locked' if review_level == 'college' else 'school_result_locked'
    published_field = 'college_published_at' if review_level == 'college' else 'school_published_at'
    result_field = 'college_review_result' if review_level == 'college' else 'school_review_result'
    node_name = '学院赛' if review_level == 'college' else '校赛'

    def _load_published_items():
        rows2 = conn.execute(
            f'''
            SELECT id, title, leader_name, college, extra_info,
                   {score_field} as avg_score, {rank_field} as rank_no,
                   {result_field} as review_result,
                   {published_field} as published_at,
                   COALESCE({lock_field}, 0) as locked
            FROM projects
            WHERE competition_id = ?
              AND {published_field} IS NOT NULL
              AND COALESCE({lock_field}, 0) = 1
            ''',
            (int(competition_id),)
        ).fetchall()

        items2 = []
        for rr in rows2 or []:
            d2 = dict(rr)
            if review_level == 'college' and scope_key:
                short2 = _normalize_scope_key_for_college(str(d2.get('college') or ''))
                if not (short2 == scope_key or scope_key in short2 or short2 in scope_key):
                    continue
            if review_level == 'school' and scope_key and scope_key != 'all':
                dg2 = ''
                try:
                    extra2 = json.loads(d2.get('extra_info') or '{}')
                    if isinstance(extra2, dict):
                        dg2 = str(extra2.get('discipline_group') or extra2.get('学科类别') or extra2.get('组别') or '')
                except Exception:
                    dg2 = ''
                if dg2 != scope_key:
                    continue
            items2.append(d2)

        items2.sort(key=lambda x: (int(x.get('rank_no') or 10**9), -float(x.get('avg_score') or 0), int(x.get('id') or 0)))
        promoted2 = sum(1 for x in items2 if str(x.get('review_result') or '').strip() == 'approved')
        return items2, promoted2

    rows = conn.execute(
        f'''
        SELECT p.id, p.title, p.leader_name, p.college, p.project_type, p.template_type, p.extra_info,
               p.status, p.current_level, p.review_stage,
               p.{score_field} as avg_score, p.{rank_field} as rank_no,
               p.college_review_result, p.school_review_result,
               COALESCE(p.{lock_field}, 0) as locked,
               COALESCE(p.department_head_opinion, '') as department_head_opinion
        FROM projects p
        WHERE p.competition_id = ?
          AND p.id IN (SELECT DISTINCT project_id FROM review_tasks WHERE review_level = ?)
          AND p.status NOT IN ('finished', 'finished_national_award', 'college_failed', 'school_failed', 'provincial_award')
        ''',
        (int(competition_id), review_level)
    ).fetchall()

    projects = []
    for r in rows:
        d = dict(r)
        st = str(d.get('status') or '').strip()
        if st == 'rejected':
            continue
        if review_level == 'college':
            allowed = {
                'pending', 'under_review', 'pending_college', 'reviewing', 'pending_college_recommendation', 'college_review',
                'college_recommended', 'school_review'
            }
            if st not in allowed:
                continue
        else:
            allowed = {
                'college_recommended', 'school_review', 'pending_school_recommendation', 'approved', 'rated', 'school_approved', 'provincial_review'
            }
            if st not in allowed:
                continue
        if review_level == 'college' and scope_key:
            c = str(d.get('college') or '')
            short = _normalize_scope_key_for_college(c)
            if not (short == scope_key or scope_key in short or short in scope_key):
                continue
        if review_level == 'school' and scope_key and scope_key != 'all':
            extra = {}
            try:
                extra = json.loads(d.get('extra_info') or '{}')
            except Exception:
                extra = {}
            dg = ''
            if isinstance(extra, dict):
                dg = str(extra.get('discipline_group') or extra.get('学科类别') or extra.get('组别') or '')
            if dg != scope_key:
                continue
        projects.append(d)

    if not projects:
        items2, promoted2 = _load_published_items()
        if items2:
            return success(data={'total': len(items2), 'promoted': promoted2, 'already_published': True, 'items': items2}, message='已发布')
        return fail('当前范围内无可发布项目', 400)

    if any(int(p.get('locked') or 0) == 1 for p in projects):
        items2, promoted2 = _load_published_items()
        if items2:
            return success(data={'total': len(items2), 'promoted': promoted2, 'already_published': True, 'items': items2}, message='已发布')
        return fail('存在已锁定项目，无法重复发布', 400)

    need_recalc = any(
        (p.get('avg_score') is not None and p.get('avg_score') != '')
        and (p.get('rank_no') is None or p.get('rank_no') == '')
        for p in projects
    )
    if need_recalc:
        _recalc_review_ranks(conn, int(competition_id), review_level)
        for p in projects:
            rr = conn.execute(f'SELECT {rank_field} as r FROM projects WHERE id = ?', (int(p['id']),)).fetchone()
            p['rank_no'] = rr['r'] if rr else p.get('rank_no')

    pending = [
        p for p in projects
        if p.get('avg_score') is None
        or p.get('avg_score') == ''
        or p.get('rank_no') is None
        or p.get('rank_no') == ''
    ]
    if pending:
        sample = [int(p['id']) for p in pending[:10]]
        return fail(message=f'仍有 {len(pending)} 个项目未产生均分/排名，请先完成评审并计算排名', code=400, data={'sample_project_ids': sample})

    manual_mode = any(str(p.get(result_field) or '').strip() in ('approved', 'rejected') for p in projects)
    if manual_mode:
        approved_ids = set(int(p['id']) for p in projects if str(p.get(result_field) or '').strip() == 'approved')
        if not approved_ids:
            return fail('请先在推荐控制台确认推荐项目进入下一阶段', 400)
        try:
            conn.execute('BEGIN TRANSACTION')
            for p in projects:
                pid = int(p['id'])
                cur_result = str(p.get(result_field) or '').strip()
                new_result = cur_result if cur_result in ('approved', 'rejected') else 'rejected'
                approved = new_result == 'approved'

                conn.execute(
                    f'''
                    UPDATE projects
                    SET {result_field} = ?,
                        {lock_field} = 1,
                        {published_field} = CURRENT_TIMESTAMP
                    WHERE id = ?
                    ''',
                    (new_result, pid)
                )

                exists_node = conn.execute(
                    'SELECT id FROM project_node_status WHERE project_id = ? AND node_name = ?',
                    (pid, node_name)
                ).fetchone()
                node_status = '已推荐' if approved else '未推荐'
                if exists_node:
                    conn.execute(
                        'UPDATE project_node_status SET current_status = ?, updated_by = ?, updated_at = CURRENT_TIMESTAMP WHERE project_id = ? AND node_name = ?',
                        (node_status, session.get('user_id'), pid, node_name)
                    )
                else:
                    conn.execute(
                        'INSERT INTO project_node_status (project_id, node_name, current_status, comment, award_level, updated_by, updated_at) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)',
                        (pid, node_name, node_status, '', '', session.get('user_id'))
                    )

            try:
                conn.execute(
                    'INSERT INTO system_logs (user_id, action, details, ip_address) VALUES (?, ?, ?, ?)',
                    (session.get('user_id'), 'PUBLISH_REVIEW_RESULTS', json.dumps({'competition_id': int(competition_id), 'review_level': review_level, 'scope_key': scope_key, 'mode': 'manual'}, ensure_ascii=False), request.remote_addr)
                )
            except Exception:
                pass

            conn.execute('COMMIT')
            return success(data={'total': len(projects), 'promoted': len(approved_ids)}, message='发布成功')
        except Exception as e:
            try:
                conn.execute('ROLLBACK')
            except Exception:
                pass
            return fail(str(e), 500)

    projects.sort(key=lambda x: (float(x.get('avg_score') or 0), -int(x.get('id') or 0)), reverse=True)
    total = len(projects)
    if rule_type == 'count':
        promote_count = int(math.floor(float(rule_value)))
    else:
        promote_count = int(math.ceil(total * float(rule_value) / 100.0))
    promote_count = max(0, min(total, promote_count))
    promoted_ids = set(int(p['id']) for p in projects[:promote_count])

    try:
        conn.execute('BEGIN TRANSACTION')

        for p in projects:
            pid = int(p['id'])
            approved = pid in promoted_ids
            new_result = 'approved' if approved else 'rejected'
            is_big_challenge = str(p.get('project_type') or '').strip() == 'challenge_cup' or str(p.get('template_type') or '').strip() == 'challenge_cup'
            conn.execute(
                f'''
                UPDATE projects
                SET {result_field} = ?,
                    {lock_field} = 1,
                    {published_field} = CURRENT_TIMESTAMP
                WHERE id = ?
                ''',
                (new_result, pid)
            )

            exists_node = conn.execute(
                'SELECT id FROM project_node_status WHERE project_id = ? AND node_name = ?',
                (pid, node_name)
            ).fetchone()
            node_status = '已推荐' if approved else '未推荐'
            if exists_node:
                conn.execute(
                    'UPDATE project_node_status SET current_status = ?, updated_by = ?, updated_at = CURRENT_TIMESTAMP WHERE project_id = ? AND node_name = ?',
                    (node_status, session.get('user_id'), pid, node_name)
                )
            else:
                conn.execute(
                    'INSERT INTO project_node_status (project_id, node_name, current_status, comment, award_level, updated_by, updated_at) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)',
                    (pid, node_name, node_status, '', '', session.get('user_id'))
                )

            if review_level == 'college' and (not approved):
                conn.execute(
                    "DELETE FROM review_tasks WHERE project_id = ? AND review_level = ?",
                    (pid, 'school')
                )
                conn.execute(
                    "UPDATE projects SET status = 'rejected', current_level = 'college', review_stage = 'college' WHERE id = ?",
                    (pid,)
                )
                try:
                    conn.execute(
                        "UPDATE project_node_status SET current_status = '' WHERE project_id = ? AND node_name IN ('校赛','省赛','国赛')",
                        (pid,)
                    )
                except Exception:
                    pass

            if review_level == 'college':
                if approved:
                    if not (p.get('department_head_opinion') or '').strip():
                        conn.execute('UPDATE projects SET department_head_opinion = ? WHERE id = ?', ('同意推荐', pid))

                    conn.execute(
                        '''
                        UPDATE projects
                        SET current_level = 'school',
                            review_stage = 'school',
                            status = CASE
                                WHEN status IN ('pending', 'under_review', 'college_review', 'reviewing') THEN 'college_recommended'
                                ELSE status
                            END
                        WHERE id = ?
                        ''',
                        (pid,)
                    )

                    exists_next = conn.execute(
                        'SELECT id FROM project_node_status WHERE project_id = ? AND node_name = ?',
                        (pid, '校赛')
                    ).fetchone()
                    if not exists_next:
                        conn.execute(
                            'INSERT INTO project_node_status (project_id, node_name, current_status, comment, award_level, updated_by, updated_at) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)',
                            (pid, '校赛', '待评审', '', '', session.get('user_id'))
                        )

                    discipline_group = str(data.get('discipline_group') or '').strip()
                    try:
                        ei = json.loads(p.get('extra_info') or '{}')
                        if isinstance(ei, dict) and ei.get('discipline_group'):
                            discipline_group = str(ei.get('discipline_group'))
                    except Exception:
                        pass
                    if not discipline_group:
                        discipline_group = '理工组'

                    team = conn.execute(
                        'SELECT id FROM review_teams WHERE level = ? AND discipline_group = ? AND enabled = 1 ORDER BY id LIMIT 1',
                        ('school', discipline_group)
                    ).fetchone()
                    if not team:
                        team = conn.execute(
                            'SELECT id FROM review_teams WHERE level = ? AND enabled = 1 ORDER BY id LIMIT 1',
                            ('school',)
                        ).fetchone()
                    if team:
                        members = conn.execute(
                            'SELECT user_id FROM review_team_members WHERE team_id = ?',
                            (team['id'],)
                        ).fetchall()
                        for m in members:
                            t_exists = conn.execute(
                                'SELECT id FROM review_tasks WHERE project_id = ? AND judge_id = ? AND review_level = ?',
                                (pid, m['user_id'], 'school')
                            ).fetchone()
                            if t_exists:
                                continue
                            conn.execute(
                                'INSERT INTO review_tasks (project_id, judge_id, review_level, team_id, status, score, comments) VALUES (?, ?, ?, ?, ?, ?, ?)',
                                (pid, m['user_id'], 'school', team['id'], 'pending', 0, '')
                            )
                            try:
                                meta_json = json.dumps({'route': '/', 'query': {'tab': 'my_reviews', 'task': 'review_task', 'pid': int(pid)}, 'project_id': int(pid)}, ensure_ascii=False)
                            except Exception:
                                meta_json = None
                            conn.execute(
                                'INSERT INTO notifications (user_id, title, content, type, meta) VALUES (?, ?, ?, ?, ?)',
                                (m['user_id'], '新增校赛评审任务', f'项目《{p["title"]}》已进入校赛，请在“我的评审任务”中完成评审。', 'project', meta_json)
                            )
                else:
                    if is_big_challenge:
                        conn.execute(
                            '''
                            UPDATE projects
                            SET status = 'college_failed',
                                current_level = 'college',
                                review_stage = 'college'
                            WHERE id = ?
                            ''',
                            (pid,)
                        )
                        conn.execute(
                            "DELETE FROM review_tasks WHERE project_id = ? AND review_level = ?",
                            (pid, 'school')
                        )
                        try:
                            conn.execute(
                                "UPDATE project_node_status SET current_status = '' WHERE project_id = ? AND node_name IN ('校赛','省赛','国赛')",
                                (pid,)
                            )
                        except Exception:
                            pass
                    else:
                        conn.execute(
                            '''
                            UPDATE projects
                            SET status = 'rejected',
                                current_level = 'college',
                                review_stage = 'college'
                            WHERE id = ?
                            ''',
                            (pid,)
                        )
                        conn.execute(
                            "DELETE FROM review_tasks WHERE project_id = ? AND review_level = ?",
                            (pid, 'school')
                        )
                        try:
                            conn.execute(
                                "UPDATE project_node_status SET current_status = '' WHERE project_id = ? AND node_name IN ('校赛','省赛','国赛')",
                                (pid,)
                            )
                        except Exception:
                            pass
            elif review_level == 'school' and (not approved) and is_big_challenge:
                conn.execute(
                    '''
                    UPDATE projects
                    SET status = 'school_failed',
                        current_level = 'school',
                        review_stage = 'school'
                    WHERE id = ?
                    ''',
                    (pid,)
                )
                try:
                    conn.execute(
                        "UPDATE project_node_status SET current_status = '' WHERE project_id = ? AND node_name IN ('省赛','国赛')",
                        (pid,)
                    )
                except Exception:
                    pass

        try:
            conn.execute(
                'INSERT INTO system_logs (user_id, action, details, ip_address) VALUES (?, ?, ?, ?)',
                (session.get('user_id'), 'PUBLISH_REVIEW_RESULTS', json.dumps({'competition_id': int(competition_id), 'review_level': review_level, 'scope_key': scope_key, 'rule_type': rule_type, 'rule_value': rule_value, 'promote_count': promote_count}, ensure_ascii=False), request.remote_addr)
            )
        except Exception:
            pass

        conn.execute('COMMIT')
        return success(data={'total': total, 'promoted': promote_count}, message='发布成功')
    except Exception as e:
        try:
            conn.execute('ROLLBACK')
        except Exception:
            pass
        return fail(str(e), 500)

@reviews_bp.route('/tasks/<int:task_id>', methods=['POST'])
@login_required
def submit_task(task_id):
    user_id = session.get('user_id')
    data = request.json or {}
    is_temporary = bool(data.get('is_temporary', False))
    status = 'pending' if is_temporary else 'completed'
    comments = (data.get('comments') or '').strip()
    criteria_scores = data.get('criteria_scores') or {}  # {scientific: 30, ...}
    score_reasons = data.get('score_reasons') or {}  # {scientific: "...", ...}
    is_recommended = bool(data.get('is_recommended', False))
    declaration = bool(data.get('declaration', False))
    not_recommended_reasons = data.get('not_recommended_reasons') or []
    
    if not isinstance(criteria_scores, dict):
        return fail('评分数据格式错误', 400)
    if not isinstance(score_reasons, dict):
        return fail('评分理由数据格式错误', 400)
    if not isinstance(not_recommended_reasons, list):
        return fail('不推荐原因格式错误', 400)
    
    if not is_temporary and not declaration:
        return fail('必须勾选回避声明', 400)
        
    if not is_temporary and not comments:
        return fail('综合评审意见不能为空', 400)

    if not is_temporary and not is_recommended and not not_recommended_reasons:
        return fail('请至少选择一个不推荐原因', 400)
        
    conn = get_db_connection()
    task = conn.execute('SELECT * FROM review_tasks WHERE id = ? AND judge_id = ?', (task_id, user_id)).fetchone()
    if not task:
        return fail('任务不存在或无权限', 404)
        
    if task['status'] == 'completed':
        return fail('任务已提交，不可修改', 400)
        
    parsed_scores = {}
    for k, v in criteria_scores.items():
        try:
            parsed_scores[k] = float(v)
        except Exception:
            return fail(f'{k}评分格式错误', 400)
            
    total_score = sum(parsed_scores.values())
    
    # 构造 score_details JSON
    score_details = {}
    for k in parsed_scores:
        score_details[k] = {
            'score': parsed_scores[k],
            'reason': score_reasons.get(k, '')
        }
    
    try:
        conn.execute('BEGIN TRANSACTION')
        conn.execute('''
            UPDATE review_tasks 
            SET status = ?, score = ?, comments = ?, score_details = ?, 
                is_temporary = ?, declaration = ?, is_recommended = ?,
                not_recommended_reasons = ?
            WHERE id = ?
        ''', (status, total_score, comments, json.dumps(score_details), 
              1 if is_temporary else 0, 1 if declaration else 0, 1 if is_recommended else 0,
              json.dumps(not_recommended_reasons), task_id))
                     
        # 同步更新旧的 review_scores 表以保持兼容
        conn.execute('DELETE FROM review_scores WHERE task_id = ?', (task_id,))
        for k, v in parsed_scores.items():
            conn.execute('INSERT INTO review_scores (task_id, criteria, score, max_score) VALUES (?, ?, ?, ?)',
                         (task_id, k, int(round(v)), 100)) # max_score here is dummy
                         
        conn.execute('COMMIT')
        
        # 检查是否该项目的所有评委都已提交
        if not is_temporary:
            check_and_finalize_project_review(task['project_id'], task['review_level'])
            
        return success(message='保存成功' if is_temporary else '提交成功')
    except Exception as e:
        conn.execute('ROLLBACK')
        return fail(str(e), 500)

def check_and_finalize_project_review(project_id, review_level):
    """
    检查项目在当前级别的评审是否全部完成，若完成则计算平均分并流转状态
    """
    conn = get_db_connection()
    # 获取该项目在当前级别的所有任务
    tasks = conn.execute('SELECT * FROM review_tasks WHERE project_id = ? AND review_level = ?', (project_id, review_level)).fetchall()
    
    if not tasks:
        return
        
    # 检查是否全部已提交 (status='completed')
    all_done = all(t['status'] == 'completed' for t in tasks)
    if not all_done:
        return
        
    # 计算平均分
    scores = [t['score'] for t in tasks]
    avg_score = sum(scores) / len(scores) if scores else 0
    
    # 统计推荐票数 (假设过半推荐即为推荐)
    recommended_count = sum(1 for t in tasks if t['is_recommended'] == 1)
    is_recommended = 1 if recommended_count > (len(tasks) / 2) else 0

    try:
        project = conn.execute(
            '''
            SELECT
                p.id,
                p.status,
                p.title,
                p.created_by,
                p.college,
                p.project_type,
                p.template_type,
                p.competition_id,
                c.template_type AS competition_template_type,
                c.title AS competition_title
            FROM projects p
            LEFT JOIN competitions c ON p.competition_id = c.id
            WHERE p.id = ?
            ''',
            (project_id,)
        ).fetchone()
        if project:
            from app.projects.views import resolve_template_name
            tpl_name = resolve_template_name(project)

            if tpl_name == '大挑' and review_level in ['college', 'school']:
                new_project_status = 'pending_college_recommendation' if review_level == 'college' else 'pending_school_recommendation'
                score_col = 'college_avg_score' if review_level == 'college' else 'school_avg_score'
                keep_level = 'college' if review_level == 'college' else 'school'

                conn.execute(
                    f'''
                    UPDATE projects
                    SET status = ?,
                        {score_col} = ?,
                        is_recommended = ?,
                        current_level = ?,
                        review_stage = ?
                    WHERE id = ?
                    ''',
                    (new_project_status, avg_score, is_recommended, keep_level, keep_level, project_id)
                )

                try:
                    from app.projects.views import create_project_related_notifications, create_role_notifications
                    title = str(project.get('title') or '').strip() or f'项目ID {project_id}'
                    if review_level == 'college':
                        create_project_related_notifications(
                            conn,
                            project_id,
                            '学院赛评审已完成',
                            f'您的项目《{title}》学院赛评审已完成，当前状态：待学院确认推荐。',
                            include_advisor=False,
                            exclude_user_id=session.get('user_id')
                        )
                        college = str(project.get('college') or '').strip() or None
                        create_role_notifications(
                            conn,
                            ROLES['COLLEGE_APPROVER'],
                            '待学院确认推荐',
                            f'项目《{title}》学院赛评审已完成，请在“评审管理(管理员)”中确认是否推荐至校赛。',
                            college=college,
                            exclude_user_id=session.get('user_id'),
                            meta={'project_id': project_id, 'stage': 'college'}
                        )
                    else:
                        create_project_related_notifications(
                            conn,
                            project_id,
                            '校赛评审已完成',
                            f'您的项目《{title}》校赛评审已完成，当前状态：待学校确认推荐。',
                            include_advisor=False,
                            exclude_user_id=session.get('user_id')
                        )
                        create_role_notifications(
                            conn,
                            ROLES['SCHOOL_APPROVER'],
                            '待学校确认推荐',
                            f'项目《{title}》校赛评审已完成，请在“评审管理(管理员)”中确认是否推荐至省赛。',
                            college=None,
                            exclude_user_id=session.get('user_id'),
                            meta={'project_id': project_id, 'stage': 'school'}
                        )
                except Exception:
                    pass
            else:
                if review_level == 'college':
                    new_status = 'school_review' if is_recommended else 'college_failed'
                    conn.execute(
                        '''
                        UPDATE projects
                        SET status = ?, college_avg_score = ?, is_recommended = ?
                        WHERE id = ?
                        ''',
                        (new_status, avg_score, is_recommended, project_id)
                    )
                elif review_level == 'school':
                    conn.execute(
                        '''
                        UPDATE projects
                        SET school_avg_score = ?, is_recommended = ?
                        WHERE id = ?
                        ''',
                        (avg_score, is_recommended, project_id)
                    )

            if review_level == 'college' and tpl_name == '大创创新训练' and project.get('project_type') == 'innovation':
                conn.execute(
                    '''
                    UPDATE projects
                    SET status = ?, college_avg_score = ?, is_recommended = ?
                    WHERE id = ?
                    ''',
                    ('college_recommended' if is_recommended else 'rejected', avg_score, is_recommended, project_id)
                )
            if review_level == 'school' and tpl_name == '大创创新训练' and project.get('project_type') == 'innovation':
                conn.execute(
                    '''
                    UPDATE projects
                    SET status = ?, school_avg_score = ?, is_recommended = ?, current_level = ?, review_stage = ?
                    WHERE id = ?
                    ''',
                    ('rated' if is_recommended else 'rejected', avg_score, is_recommended, 'school', 'school', project_id)
                )
            struct_row = conn.execute(
                'SELECT process_structure FROM process_templates WHERE template_name = ?',
                (tpl_name,)
            ).fetchone() if tpl_name else None
            try:
                struct = json.loads(struct_row['process_structure'] or '[]') if struct_row else []
            except Exception:
                struct = []
                
            node_name = None
            if tpl_name == '大挑':
                node_name = '学院赛' if review_level == 'college' else ('校赛' if review_level == 'school' else None)
            if not node_name and struct:
                if review_level == 'college':
                    node_name = struct[0]
                elif review_level == 'school':
                    node_name = '校赛' if '校赛' in struct else struct[0]
            
            if node_name:
                node_status = '待确认' if (tpl_name == '大挑' and review_level in ['college', 'school']) else ('已推荐' if is_recommended else '未推荐')
                
                conn.execute(
                    '''
                    INSERT INTO project_node_status (project_id, node_name, current_status, comment, award_level, updated_by, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(project_id, node_name) DO UPDATE SET
                        current_status=excluded.current_status,
                        comment=excluded.comment,
                        award_level=excluded.award_level,
                        updated_by=excluded.updated_by,
                        updated_at=CURRENT_TIMESTAMP
                    ''',
                    (project_id, node_name, node_status, '', '', session.get('user_id'),)
                )
                
                # 只有非大挑学院赛/校赛的情况才自动流转到下一个节点
                is_manual_confirm_required = (tpl_name == '大挑' and review_level in ['college', 'school'])
                
                if not is_manual_confirm_required and is_recommended and struct and node_name in struct:
                    idx = struct.index(node_name)
                    if idx + 1 < len(struct):
                        next_node = struct[idx + 1]
                        conn.execute(
                            '''
                            INSERT INTO project_node_status (project_id, node_name, current_status, comment, award_level, updated_by, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                            ON CONFLICT(project_id, node_name) DO NOTHING
                            ''',
                            (project_id, next_node, '待评审', '', '', session.get('user_id'))
                        )
                        
                if tpl_name == '大挑' and not is_manual_confirm_required:
                    if review_level == 'college':
                        conn.execute(
                            '''
                            UPDATE projects
                            SET current_level = ?, review_stage = ?, college_review_result = ?
                            WHERE id = ?
                            ''',
                            ('school' if is_recommended else 'college', 'school' if is_recommended else 'college',
                             'approved' if is_recommended else 'rejected', project_id)
                        )
                    elif review_level == 'school':
                        conn.execute(
                            '''
                            UPDATE projects
                            SET current_level = ?, review_stage = ?, school_review_result = ?
                            WHERE id = ?
                            ''',
                            ('provincial' if is_recommended else 'school', 'provincial' if is_recommended else 'school',
                             'approved' if is_recommended else 'rejected', project_id)
                        )
            try:
                if project and project.get('competition_id'):
                    _recalc_review_ranks(conn, int(project.get('competition_id')), review_level)
            except Exception:
                pass
    except Exception:
        pass
        
    conn.commit()

@reviews_bp.route('/college/confirm-recommendations', methods=['POST'])
@login_required
def confirm_college_recommendations():
    """
    学院管理员手动确认推荐项目到校赛
    """
    if session.get('role') not in ['college_approver', 'system_admin']:
        return fail('权限不足', 403)
        
    data = request.json
    project_ids = data.get('project_ids', [])
    opinion = data.get('department_head_opinion', '')
    
    if not project_ids:
        return fail('请选择要推荐的项目', 400)
    if not opinion:
        return fail('请填写院系负责人意见', 400)
        
    conn = get_db_connection()
    try:
        conn.execute('BEGIN TRANSACTION')
        for p_id in project_ids:
            p = conn.execute('SELECT id, title FROM projects WHERE id = ?', (p_id,)).fetchone()
            p_title = str(p['title'] or '').strip() if p else f'项目ID {p_id}'
            # 更新项目状态和意见
            conn.execute('''
                UPDATE projects 
                SET status = ?, 
                    current_level = ?, 
                    review_stage = ?, 
                    college_review_result = ?,
                    department_head_opinion = ?
                WHERE id = ?
            ''', ('school_review', 'school', 'school', 'approved', opinion, p_id))
            
            # 更新流程节点状态
            conn.execute('''
                INSERT INTO project_node_status (project_id, node_name, current_status, updated_by, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(project_id, node_name) DO UPDATE SET
                    current_status=excluded.current_status,
                    updated_by=excluded.updated_by,
                    updated_at=CURRENT_TIMESTAMP
            ''', (p_id, '学院赛', '已推荐', session.get('user_id')))
            try:
                conn.execute(
                    'UPDATE project_node_status SET comment = ? WHERE project_id = ? AND node_name = ?',
                    (opinion, p_id, '学院赛')
                )
            except Exception:
                pass
            
            # 自动开启校赛节点
            conn.execute('''
                INSERT INTO project_node_status (project_id, node_name, current_status, updated_by, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(project_id, node_name) DO NOTHING
            ''', (p_id, '校赛', '待评审', session.get('user_id')))

            try:
                from app.projects.views import create_project_related_notifications
                create_project_related_notifications(
                    conn,
                    p_id,
                    '已推荐至校赛',
                    f'您的项目《{p_title}》已由学院管理员确认推荐至校赛，请关注后续评审安排。',
                    include_advisor=False,
                    exclude_user_id=session.get('user_id'),
                )
            except Exception:
                pass
            
        conn.commit()
        return success(message=f'成功推荐 {len(project_ids)} 个项目到校赛')
    except Exception as e:
        conn.execute('ROLLBACK')
        return fail(f'推荐失败: {str(e)}', 500)

@reviews_bp.route('/school/confirm-recommendations', methods=['POST'])
@login_required
def confirm_school_recommendations():
    """
    学校管理员手动确认推荐项目到省赛
    """
    if session.get('role') not in ['school_approver', 'project_admin', 'system_admin']:
        return fail('权限不足', 403)
        
    data = request.json
    project_ids = data.get('project_ids', [])
    opinion_date = str(data.get('opinion_date') or '').strip()
    base_phrase = '经审核，情况属实，同意推荐'
    opinion = base_phrase
    
    if not project_ids:
        return fail('请选择要推荐的项目', 400)
    if not opinion_date:
        return fail('请填写意见日期', 400)
    try:
        datetime.strptime(opinion_date, '%Y-%m-%d')
    except Exception:
        return fail('意见日期格式错误，应为 YYYY-MM-DD', 400)
    opinion_text = f'{base_phrase}（{opinion_date}）'
        
    conn = get_db_connection()
    try:
        conn.execute('BEGIN TRANSACTION')
        for p_id in project_ids:
            p = conn.execute('SELECT id, title FROM projects WHERE id = ?', (p_id,)).fetchone()
            p_title = str(p['title'] or '').strip() if p else f'项目ID {p_id}'
            # 更新项目状态和意见
            conn.execute('''
                UPDATE projects 
                SET status = ?, 
                    current_level = ?, 
                    review_stage = ?, 
                    school_review_result = ?,
                    research_admin_opinion = ?
                WHERE id = ?
            ''', ('provincial_review', 'provincial', 'provincial', 'approved', opinion_text, p_id))
            
            # 更新流程节点状态
            conn.execute('''
                INSERT INTO project_node_status (project_id, node_name, current_status, updated_by, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(project_id, node_name) DO UPDATE SET
                    current_status=excluded.current_status,
                    updated_by=excluded.updated_by,
                    updated_at=CURRENT_TIMESTAMP
            ''', (p_id, '校赛', '已推荐', session.get('user_id')))
            try:
                conn.execute(
                    'UPDATE project_node_status SET comment = ? WHERE project_id = ? AND node_name = ?',
                    (opinion_text, p_id, '校赛')
                )
            except Exception:
                pass
            
            # 自动开启省赛节点
            conn.execute('''
                INSERT INTO project_node_status (project_id, node_name, current_status, updated_by, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(project_id, node_name) DO UPDATE SET
                    current_status = CASE
                        WHEN COALESCE(TRIM(project_node_status.current_status), '') IN ('', '未晋级', '待评审') THEN excluded.current_status
                        ELSE project_node_status.current_status
                    END,
                    updated_by = excluded.updated_by,
                    updated_at = CURRENT_TIMESTAMP
            ''', (p_id, '省赛', '待评审', session.get('user_id')))

            try:
                from app.projects.views import create_project_related_notifications
                create_project_related_notifications(
                    conn,
                    p_id,
                    '已推荐至省赛',
                    f'您的项目《{p_title}》已由学校管理员确认推荐至省赛，请关注后续评审安排。',
                    include_advisor=False,
                    exclude_user_id=session.get('user_id'),
                )
            except Exception:
                pass
            
        conn.commit()
        return success(message=f'成功推荐 {len(project_ids)} 个项目到省赛')
    except Exception as e:
        conn.execute('ROLLBACK')
        return fail(f'推荐失败: {str(e)}', 500)

@reviews_bp.route('/project/<int:project_id>/review-status', methods=['GET'])
@login_required
def get_project_review_status(project_id):
    """
    获取项目在学院赛和校赛的评审状态（是否全部完成、当前用户是否为组长）
    """
    user_id = session.get('user_id')
    conn = get_db_connection()
    
    # 1. 获取所有评审任务
    tasks = conn.execute('''
        SELECT judge_id, review_level, status, team_id
        FROM review_tasks 
        WHERE project_id = ?
    ''', (project_id,)).fetchall()
    
    # 2. 获取当前用户在相关团队中的角色
    team_ids = list(set([t['team_id'] for t in tasks if t['team_id']]))
    roles = {}
    if team_ids:
        placeholders = ','.join(['?'] * len(team_ids))
        member_rows = conn.execute(f'''
            SELECT team_id, role_in_team 
            FROM review_team_members 
            WHERE user_id = ? AND team_id IN ({placeholders})
        ''', [user_id] + team_ids).fetchall()
        roles = {r['team_id']: r['role_in_team'] for r in member_rows}
    
    # 3. 统计状态
    levels = ['college', 'school']
    status_data = {}
    
    for lv in levels:
        lv_tasks = [t for t in tasks if t['review_level'] == lv]
        if not lv_tasks:
            status_data[lv] = {
                'all_completed': False,
                'is_leader': False,
                'total_count': 0,
                'completed_count': 0
            }
            continue
            
        all_completed = all(t['status'] == 'completed' for t in lv_tasks)
        # 只要在其中一个相关团队中是组长即可（通常一个级别只有一个团队）
        is_leader = any(roles.get(t['team_id']) == 'leader' for t in lv_tasks if t['team_id'])
        
        status_data[lv] = {
            'all_completed': all_completed,
            'is_leader': is_leader,
            'total_count': len(lv_tasks),
            'completed_count': sum(1 for t in lv_tasks if t['status'] == 'completed')
        }
        
    return success(data=status_data)

@reviews_bp.route('/assign', methods=['POST'])
@login_required
@role_required([ROLES['COLLEGE_APPROVER'], ROLES['SCHOOL_APPROVER'], ROLES['PROJECT_ADMIN'], ROLES['SYSTEM_ADMIN']])
def assign_reviewers():
    data = request.json
    project_id = data.get('project_id')
    judge_ids = data.get('judge_ids', [])
    review_level = data.get('review_level', 'college')
    force = data.get('force', False) # 是否强制分配（忽略回避规则）
    
    if not project_id or not judge_ids:
        return fail('参数不完整', 400)
        
    conn = get_db_connection()
    try:
        p = conn.execute('SELECT id, status, title, current_level, review_stage, college_review_result, school_review_result FROM projects WHERE id = ?', (project_id,)).fetchone()
        if not p:
            return fail('项目不存在', 404)
        st = str(p['status'] or '').strip()
        if st in ['finished', 'finished_national_award', 'college_failed', 'school_failed', 'provincial_award']:
            return fail('项目已结项，不可再分配评委', 400)
        cl = str(p['current_level'] or '').strip()
        rs = str(p['review_stage'] or '').strip()
        if review_level == 'school':
            if not (cl == 'school' or rs == 'school' or st in ['school_review', 'college_recommended', 'pending_school_recommendation']):
                return fail('项目未进入校赛阶段，不能分配校赛评审任务', 400)
        if review_level == 'college':
            if not (cl == 'college' or rs == 'college' or st in ['pending', 'under_review', 'pending_college', 'reviewing', 'pending_college_recommendation']):
                return fail('项目未进入学院赛阶段，不能分配学院赛评审任务', 400)

        conn.execute('BEGIN TRANSACTION')
        assigned_count = 0
        conflicts = []
        
        for j_id in judge_ids:
            # 智能回避检测
            if not force:
                conflict_reason = check_reviewer_conflict(conn, j_id, project_id)
                if conflict_reason:
                    conflicts.append({'judge_id': j_id, 'reason': conflict_reason})
                    continue
            
            # Check if already assigned
            existing = conn.execute('SELECT id FROM review_tasks WHERE project_id = ? AND judge_id = ? AND review_level = ?',
                                    (project_id, j_id, review_level)).fetchone()
            if not existing:
                conn.execute('''
                    INSERT INTO review_tasks (project_id, judge_id, review_level, status, score, comments, is_conflict, conflict_reason) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (project_id, j_id, review_level, 'pending', 0, '', 1 if conflict_reason else 0, conflict_reason))
                
                # 发送消息通知
                level_text = '学院赛' if review_level == 'college' else '校赛'
                conn.execute(
                    'INSERT INTO notifications (user_id, title, content, type) VALUES (?, ?, ?, ?)',
                    (j_id, f'新增{level_text}评审任务', f'项目《{p["title"]}》已有新的评审任务分配给您，请在“我的评审任务”中查看并处理。', 'project')
                )
                
                assigned_count += 1
        
        if conflicts and assigned_count == 0 and not force:
            conn.execute('ROLLBACK')
            return fail(data={'conflicts': conflicts}, message='存在利益冲突，分配失败。请手动干预或强制分配。', code=409)
            
        conn.execute('COMMIT')
        return success(data={'assigned_count': assigned_count, 'conflicts_skipped': len(conflicts)}, message='分配成功')
    except Exception as e:
        conn.execute('ROLLBACK')
        return fail(str(e), 500)

@reviews_bp.route('/auto_assign', methods=['POST'])
@login_required
@role_required([ROLES['COLLEGE_APPROVER'], ROLES['SCHOOL_APPROVER'], ROLES['PROJECT_ADMIN'], ROLES['SYSTEM_ADMIN']])
def auto_assign_reviewers():
    data = request.json or {}
    project_id = data.get('project_id')
    review_level = str(data.get('review_level') or 'college').strip()
    if not project_id:
        return fail('参数不完整', 400)
    if review_level not in ['college', 'school']:
        return fail('评审级别非法', 400)

    role = session.get('role')
    if role == ROLES['COLLEGE_APPROVER'] and review_level != 'college':
        return fail('无权限', 403)
    if role == ROLES['SCHOOL_APPROVER'] and review_level != 'school':
        return fail('无权限', 403)

    conn = get_db_connection()
    project = conn.execute('SELECT * FROM projects WHERE id = ?', (int(project_id),)).fetchone()
    if not project:
        return fail('项目不存在', 404)
    p = dict(project)
    st = str(p.get('status') or '').strip()
    if st in ['finished', 'finished_national_award', 'college_failed', 'school_failed', 'provincial_award']:
        return fail('项目已结项，不可再分配评委', 400)
    cl = str(p.get('current_level') or '').strip()
    rs = str(p.get('review_stage') or '').strip()
    if review_level == 'school':
        if not (cl == 'school' or rs == 'school' or st in ['school_review', 'college_recommended', 'pending_school_recommendation']):
            return fail('项目未进入校赛阶段，不能分配校赛评审任务', 400)
    if review_level == 'college':
        if not (cl == 'college' or rs == 'college' or st in ['pending', 'under_review', 'pending_college', 'reviewing', 'pending_college_recommendation']):
            return fail('项目未进入学院赛阶段，不能分配学院赛评审任务', 400)
    discipline_group = str(data.get('discipline_group') or '').strip()
    try:
        ei = json.loads(p.get('extra_info') or '{}')
        if isinstance(ei, dict):
            if not discipline_group and ei.get('discipline_group'):
                discipline_group = str(ei.get('discipline_group'))
    except Exception:
        pass
    if not discipline_group:
        discipline_group = '理工组'

    team = None
    if review_level == 'college':
        team = conn.execute(
            'SELECT * FROM review_teams WHERE level = ? AND college = ? AND enabled = 1 ORDER BY id LIMIT 1',
            ('college', p.get('college'))
        ).fetchone()
        if not team and p.get('college'):
            short_name = str(p.get('college') or '').split('（')[0].split('(')[0].strip()
            team = conn.execute(
                'SELECT * FROM review_teams WHERE level = ? AND college LIKE ? AND enabled = 1 ORDER BY id LIMIT 1',
                ('college', f"{short_name}%")
            ).fetchone()
        if not team:
            team = conn.execute(
                'SELECT * FROM review_teams WHERE level = ? AND enabled = 1 ORDER BY id LIMIT 1',
                ('college',)
            ).fetchone()
    else:
        team = conn.execute(
            'SELECT * FROM review_teams WHERE level = ? AND discipline_group = ? AND enabled = 1 ORDER BY id LIMIT 1',
            ('school', discipline_group)
        ).fetchone()
        if not team:
            team = conn.execute(
                'SELECT * FROM review_teams WHERE level = ? AND enabled = 1 ORDER BY id LIMIT 1',
                ('school',)
            ).fetchone()

    if not team:
        return fail('未找到可用评审团队', 400)

    members = conn.execute(
        '''
        SELECT rtm.user_id
        FROM review_team_members rtm
        JOIN users u ON rtm.user_id = u.id
        WHERE rtm.team_id = ?
        ''',
        (team['id'],)
    ).fetchall()
    if not members:
        return fail('评审团队没有成员', 400)

    created = 0
    try:
        conn.execute('BEGIN TRANSACTION')
        for m in members:
            existing = conn.execute(
                'SELECT id FROM review_tasks WHERE project_id = ? AND judge_id = ? AND review_level = ?',
                (int(project_id), int(m['user_id']), review_level)
            ).fetchone()
            if existing:
                continue
            conn.execute(
                'INSERT INTO review_tasks (project_id, judge_id, review_level, team_id, status, score, comments) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (int(project_id), int(m['user_id']), review_level, int(team['id']), 'pending', 0, '')
            )
            
            # 发送消息通知
            level_text = '学院赛' if review_level == 'college' else '校赛'
            conn.execute(
                'INSERT INTO notifications (user_id, title, content, type) VALUES (?, ?, ?, ?)',
                (m['user_id'], f'新增{level_text}评审任务', f'项目《{p["title"]}》已有新的评审任务分配给您，请在“我的评审任务”中查看并处理。', 'project')
            )
            
            created += 1
        if str(p.get('status') or '').strip() == 'pending':
            conn.execute('UPDATE projects SET status = ? WHERE id = ?', ('under_review', int(project_id)))
        conn.execute('COMMIT')
        return success(data={'created_tasks': created, 'team_id': int(team['id'])}, message='自动分配成功')
    except Exception as e:
        try:
            conn.execute('ROLLBACK')
        except Exception:
            pass
        return fail(str(e), 500)

@reviews_bp.route('/calc_rank', methods=['POST'])
@login_required
@role_required([ROLES['COLLEGE_APPROVER'], ROLES['SCHOOL_APPROVER'], ROLES['PROJECT_ADMIN'], ROLES['SYSTEM_ADMIN']])
def calc_rank():
    data = request.json or {}
    review_level = str(data.get('review_level', 'college')).strip()
    if review_level not in ['college', 'school']:
        return fail('review_level 非法', 400)
    
    conn = get_db_connection()
    
    # 1. Calculate average scores for projects in this level
    query = '''
        SELECT project_id, AVG(score) as avg_score
        FROM review_tasks
        WHERE review_level = ? AND status = 'completed'
        GROUP BY project_id
    '''
    avg_scores = conn.execute(query, (review_level,)).fetchall()
    
    try:
        conn.execute('BEGIN TRANSACTION')
        score_field = f'{review_level}_avg_score'
        rank_field = f'{review_level}_rank'
        for row in avg_scores:
            conn.execute(f'UPDATE projects SET {score_field} = ? WHERE id = ?', (row['avg_score'], row['project_id']))
            
        # 2. Calculate ranks partitioned by competition_id
        competitions = conn.execute('SELECT DISTINCT competition_id FROM projects WHERE competition_id IS NOT NULL').fetchall()
        for comp in competitions:
            c_id = comp['competition_id']
            conn.execute(f'UPDATE projects SET {rank_field} = NULL WHERE competition_id = ?', (c_id,))
            if review_level == 'college':
                rows = conn.execute(
                    f'''
                    SELECT id, {score_field} as score, college
                    FROM projects
                    WHERE competition_id = ?
                      AND id IN (SELECT DISTINCT project_id FROM review_tasks WHERE review_level = ?)
                      AND status IN ('pending', 'under_review', 'pending_college', 'reviewing', 'pending_college_recommendation', 'college_review', 'college_recommended', 'school_review')
                      AND {score_field} IS NOT NULL
                    ''',
                    (c_id, review_level)
                ).fetchall()
                rows = [dict(r) for r in (rows or [])]

                grouped = {}
                for r in rows:
                    key = _normalize_scope_key_for_college(str(r.get('college') or ''))
                    grouped.setdefault(key, []).append(r)

                for _, items in grouped.items():
                    items.sort(
                        key=lambda x: (float(x.get('score') or 0), -int(x.get('id') or 0)),
                        reverse=True
                    )
                    rank = 1
                    for p in items:
                        conn.execute(
                            f'UPDATE projects SET {rank_field} = ? WHERE id = ?',
                            (rank, p['id'])
                        )
                        rank += 1
            else:
                projects = conn.execute(
                    f'''
                    SELECT id, {score_field} as score, extra_info
                    FROM projects
                    WHERE competition_id = ?
                      AND id IN (SELECT DISTINCT project_id FROM review_tasks WHERE review_level = ?)
                      AND status IN ('college_recommended', 'school_review', 'pending_school_recommendation', 'approved', 'rated', 'school_approved', 'provincial_review')
                      AND {score_field} IS NOT NULL
                    ''',
                    (c_id, review_level)
                ).fetchall()
                projects = [dict(p) for p in (projects or [])]

                grouped = {}
                for p in projects:
                    dg = ''
                    try:
                        extra = json.loads(p.get('extra_info') or '{}')
                        if isinstance(extra, dict):
                            dg = str(extra.get('discipline_group') or extra.get('学科类别') or extra.get('组别') or '')
                    except Exception:
                        dg = ''
                    key = dg or 'all'
                    grouped.setdefault(key, []).append(p)

                for _, items in grouped.items():
                    items.sort(
                        key=lambda x: (float(x.get('score') or 0), -int(x.get('id') or 0)),
                        reverse=True
                    )
                    rank = 1
                    for p in items:
                        conn.execute(f'UPDATE projects SET {rank_field} = ? WHERE id = ?', (rank, p['id']))
                        rank += 1
            
        conn.execute('COMMIT')
        return success(message='计算完成')
    except Exception as e:
        conn.execute('ROLLBACK')
        return fail(str(e), 500)


@reviews_bp.route('/published_results', methods=['GET'])
@login_required
def published_results():
    competition_id = request.args.get('competition_id')
    review_level = str(request.args.get('review_level') or 'college').strip()
    scope_key = str(request.args.get('scope_key') or '').strip()
    if not competition_id:
        return fail('缺少 competition_id', 400)
    if review_level not in ['college', 'school']:
        return fail('review_level 非法', 400)

    if review_level == 'college':
        scope_key = _normalize_scope_key_for_college(session.get('college', '')) if session.get('role') == ROLES['COLLEGE_APPROVER'] else _normalize_scope_key_for_college(scope_key)
    else:
        scope_key = scope_key or (request.args.get('discipline_group') or 'all')

    score_field = f'{review_level}_avg_score'
    rank_field = f'{review_level}_rank'
    lock_field = 'college_result_locked' if review_level == 'college' else 'school_result_locked'
    published_field = 'college_published_at' if review_level == 'college' else 'school_published_at'
    result_field = 'college_review_result' if review_level == 'college' else 'school_review_result'

    conn = get_db_connection()
    rows = conn.execute(
        f'''
        SELECT id, title, leader_name, college, extra_info,
               {score_field} as avg_score, {rank_field} as rank_no,
               {award_field} as award,
               {result_field} as review_result,
               {published_field} as published_at,
               COALESCE({lock_field}, 0) as locked
        FROM projects
        WHERE competition_id = ?
          AND {published_field} IS NOT NULL
        ''',
        (int(competition_id),)
    ).fetchall()

    items = []
    for r in rows or []:
        d = dict(r)
        if int(d.get('locked') or 0) != 1:
            continue
        if review_level == 'college' and scope_key:
            short = _normalize_scope_key_for_college(str(d.get('college') or ''))
            if not (short == scope_key or scope_key in short or short in scope_key):
                continue
        if review_level == 'school' and scope_key and scope_key != 'all':
            dg = ''
            try:
                extra = json.loads(d.get('extra_info') or '{}')
                if isinstance(extra, dict):
                    dg = str(extra.get('discipline_group') or extra.get('学科类别') or extra.get('组别') or '')
            except Exception:
                dg = ''
            if dg != scope_key:
                continue
        items.append(d)

    items.sort(key=lambda x: (int(x.get('rank_no') or 10**9), -float(x.get('avg_score') or 0), int(x.get('id') or 0)))
    return success(data={'items': items})

@reviews_bp.route('/recommend', methods=['POST'])
@login_required
@role_required([ROLES['COLLEGE_APPROVER'], ROLES['SCHOOL_APPROVER'], ROLES['PROJECT_ADMIN'], ROLES['SYSTEM_ADMIN']])
def recommend_project():
    data = request.json
    project_id = data.get('project_id')
    next_level = data.get('next_level', 'school')
    
    if not project_id:
        return fail('参数不完整', 400)
        
    conn = get_db_connection()
    p = conn.execute('SELECT id, title, created_by, college, extra_info, status, current_level, college_review_result FROM projects WHERE id = ?', (project_id,)).fetchone()
    if not p:
        return fail('项目不存在', 404)

    if p['current_level'] == 'school' and next_level != 'school':
        return fail('项目已进入校赛阶段，不能回退', 400)
    if p['college_review_result'] == 'approved' and next_level == 'college':
        return fail('学院赛已通过，不能回退', 400)

    conn.execute('UPDATE projects SET current_level = ? WHERE id = ?', (next_level, project_id))
    if p['status'] == 'pending':
        conn.execute('UPDATE projects SET status = ? WHERE id = ?', ('under_review', project_id))

    if next_level == 'school':
        conn.execute(
            'UPDATE projects SET review_stage = ?, college_review_result = COALESCE(NULLIF(college_review_result, \'\'), ?) WHERE id = ?',
            ('school', 'approved', project_id)
        )
        exists_next = conn.execute(
            'SELECT id FROM project_node_status WHERE project_id = ? AND node_name = ?',
            (project_id, '校赛')
        ).fetchone()
        if not exists_next:
            conn.execute(
                'INSERT INTO project_node_status (project_id, node_name, current_status, comment, award_level, updated_by, updated_at) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)',
                (project_id, '校赛', '待评审', '', '', session.get('user_id'))
            )

        discipline_group = data.get('discipline_group') or '理工组'
        try:
            import json as _json
            ei = _json.loads(p['extra_info'] or '{}')
            if isinstance(ei, dict) and ei.get('discipline_group'):
                discipline_group = str(ei.get('discipline_group'))
        except Exception:
            pass

        team = conn.execute(
            'SELECT id FROM review_teams WHERE level = ? AND discipline_group = ? AND enabled = 1 ORDER BY id LIMIT 1',
            ('school', discipline_group)
        ).fetchone()
        if not team:
            team = conn.execute(
                'SELECT id FROM review_teams WHERE level = ? AND enabled = 1 ORDER BY id LIMIT 1',
                ('school',)
            ).fetchone()

        if team:
            members = conn.execute(
                'SELECT user_id FROM review_team_members WHERE team_id = ?',
                (team['id'],)
            ).fetchall()
            for m in members:
                t_exists = conn.execute(
                    'SELECT id FROM review_tasks WHERE project_id = ? AND judge_id = ? AND review_level = ?',
                    (project_id, m['user_id'], 'school')
                ).fetchone()
                if t_exists:
                    continue
                conn.execute(
                    'INSERT INTO review_tasks (project_id, judge_id, review_level, team_id, status, score, comments) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (project_id, m['user_id'], 'school', team['id'], 'pending', 0, '')
                )
                try:
                    meta_json = json.dumps({'route': '/', 'query': {'tab': 'my_reviews', 'task': 'review_task', 'pid': int(project_id)}, 'project_id': int(project_id)}, ensure_ascii=False)
                except Exception:
                    meta_json = None
                conn.execute(
                    'INSERT INTO notifications (user_id, title, content, type, meta) VALUES (?, ?, ?, ?, ?)',
                    (m['user_id'], '新增校赛评审任务', f'项目《{p["title"]}》已进入校赛，请在“我的评审任务”中完成评审。', 'project', meta_json)
                )

    conn.execute(
        'INSERT INTO notifications (user_id, title, content, type) VALUES (?, ?, ?, ?)',
        (p['created_by'], '项目阶段更新', f'你的项目《{p["title"]}》已进入{("校赛" if next_level == "school" else next_level)}阶段。', 'project')
    )

    conn.commit()
    return success(message='推荐成功')


@reviews_bp.route('/test/bootstrap', methods=['POST'])
@login_required
@role_required([ROLES['COLLEGE_APPROVER'], ROLES['SCHOOL_APPROVER'], ROLES['PROJECT_ADMIN'], ROLES['SYSTEM_ADMIN']])
def bootstrap_test_reviews():
    from flask import current_app
    import traceback
    try:
        data = request.json or {}
        project_id = data.get('project_id')
        review_level = str(data.get('review_level', 'college')).strip()
        if review_level not in ['college', 'school']:
            return fail('评审级别非法', 400)

        conn = get_db_connection()
        current_app.logger.info(f"Bootstrap reviews for project {project_id} at level {review_level}")

        project = None
        if project_id is not None:
            project = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()

        if not project:
            if review_level == 'college':
                project = conn.execute(
                    '''
                    SELECT * FROM projects
                    WHERE status IN ('pending', 'under_review', 'pending_college', 'reviewing')
                    ORDER BY id DESC LIMIT 1
                    '''
                ).fetchone()
            else:
                project = conn.execute(
                    '''
                    SELECT * FROM projects
                    WHERE status IN ('college_recommended', 'school_review', 'approved', 'rated', 'school_approved', 'pending_school_recommendation')
                    ORDER BY id DESC LIMIT 1
                    '''
                ).fetchone()
            if not project:
                project = conn.execute('SELECT * FROM projects ORDER BY id DESC LIMIT 1').fetchone()
            if not project:
                return fail('系统中尚无任何项目', 404)
            project_id = project['id']
            current_app.logger.info(f"Fallback to project {project_id}")
        else:
            project_id = project['id']
        st = str(project['status'] or '').strip()
        if st in ['finished', 'finished_national_award', 'college_failed', 'school_failed', 'provincial_award']:
            return fail('项目已终止/结项，不可初始化评审任务', 400)
        cl = str(project.get('current_level') or '').strip() if isinstance(project, dict) else str(project['current_level'] or '').strip()
        rs = str(project.get('review_stage') or '').strip() if isinstance(project, dict) else str(project['review_stage'] or '').strip()
        if review_level == 'school':
            if not (cl == 'school' or rs == 'school' or st in ['school_review', 'college_recommended', 'pending_school_recommendation']):
                return fail('项目未进入校赛阶段，不能初始化校赛评审任务', 400)
        if review_level == 'college':
            if not (cl == 'college' or rs == 'college' or st in ['pending', 'under_review', 'pending_college', 'reviewing', 'pending_college_recommendation']):
                return fail('项目未进入学院赛阶段，不能初始化学院赛评审任务', 400)

        team = None
        if review_level == 'college':
            # 1. 尝试精确匹配项目所在学院
            team = conn.execute(
                'SELECT * FROM review_teams WHERE level = ? AND college = ? AND enabled = 1 ORDER BY id LIMIT 1',
                ('college', project['college'])
            ).fetchone()
            
            if not team and project['college']:
                # 2. 尝试模糊匹配 (处理括号差异)
                short_name = project['college'].split('（')[0].split('(')[0].strip()
                team = conn.execute(
                    'SELECT * FROM review_teams WHERE level = ? AND college LIKE ? AND enabled = 1 ORDER BY id LIMIT 1',
                    ('college', f"{short_name}%")
                ).fetchone()

            if not team:
                # 3. 最后的兜底：直接找名称匹配的
                team = conn.execute(
                    'SELECT * FROM review_teams WHERE name LIKE "计算机学院%" AND enabled = 1 ORDER BY id LIMIT 1'
                ).fetchone()
        else:
            team = conn.execute(
                'SELECT * FROM review_teams WHERE level = ? AND discipline_group = ? AND enabled = 1 ORDER BY id LIMIT 1',
                ('school', data.get('discipline_group', '理工组'))
            ).fetchone()
            if not team:
                team = conn.execute(
                    'SELECT * FROM review_teams WHERE level = ? AND enabled = 1 ORDER BY id LIMIT 1',
                    ('school',)
                ).fetchone()

        if not team:
            return fail('未找到可用评审团队', 400)

        # --- 核心修复：强制同步测试组成员 ---
        if team['name'] == '计算机学院评审测试组' or (team['college'] and '计算机' in str(team['college'])):
            # 获取当前系统中正确的测试评委 ID（防止因为 ID 变化导致分配失败）
            test_judge_usernames = ['test_cc_college_judge1', 'test_cc_college_leader', 'test_cc_college_judge2']
            actual_judges = conn.execute(
                f"SELECT id FROM users WHERE username IN (?, ?, ?)", 
                test_judge_usernames
            ).fetchall()
            
            for aj in actual_judges:
                # 强制确保这些评委在团队中
                conn.execute(
                    'INSERT OR IGNORE INTO review_team_members (team_id, user_id, role_in_team) VALUES (?, ?, ?)',
                    (team['id'], aj['id'], 'member')
                )

        # 重新获取最新的团队成员列表（仅获取系统中存在的用户）
        members = conn.execute(
            '''
            SELECT rtm.user_id 
            FROM review_team_members rtm
            JOIN users u ON rtm.user_id = u.id
            WHERE rtm.team_id = ?
            ''',
            (team['id'],)
        ).fetchall()
        
        # 清理失效的成员记录
        conn.execute(
            'DELETE FROM review_team_members WHERE team_id = ? AND user_id NOT IN (SELECT id FROM users)',
            (team['id'],)
        )
        
        if not members:
            return fail('评审团队没有成员', 400)

        created = 0
        user_id = session.get('user_id')
        for m in members:
            # 增加去重检查：确保同一项目、同一评委、同一评审级别不重复分配
            existing = conn.execute(
                'SELECT id FROM review_tasks WHERE project_id = ? AND judge_id = ? AND review_level = ?',
                (project_id, m['user_id'], review_level)
            ).fetchone()
            
            if not existing:
                conn.execute(
                    'INSERT INTO review_tasks (project_id, judge_id, review_level, team_id, status, score, comments) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (project_id, m['user_id'], review_level, team['id'], 'pending', 0, '')
                )
                
                # 发送消息通知
                level_text = '学院赛' if review_level == 'college' else '校赛'
                conn.execute(
                    'INSERT INTO notifications (user_id, title, content, type) VALUES (?, ?, ?, ?)',
                    (m['user_id'], f'新增{level_text}评审任务', f'项目《{project["title"]}》已有新的评审任务分配给您，请在“我的评审任务”中查看并处理。', 'project')
                )
                
                created += 1

        if project['status'] == 'pending':
            conn.execute('UPDATE projects SET status = ? WHERE id = ?', ('under_review', project_id))

        conn.commit()
        return success(data={'created_tasks': created, 'team_id': team['id'], 'project_id': project_id}, message='初始化成功')
    except Exception as e:
        current_app.logger.error(f"Bootstrap error: {str(e)}\n{traceback.format_exc()}")
        return fail(f"初始化异常: {str(e)}", 500)
