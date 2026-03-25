from flask import Blueprint, request, session, current_app, Response
from app.utils.db import get_db_connection
from app.utils.response import success, fail
from app.utils.auth import login_required, role_required
from config import get_config
from flasgger import swag_from
import json
import os
import sqlite3
from datetime import datetime
from werkzeug.utils import secure_filename

config = get_config()
ROLES = config.ROLES
GHOST_PROJECT_IDS = config.GHOST_PROJECT_IDS

projects_bp = Blueprint('projects', __name__, url_prefix='/api')

# Helper for notifications (moved from app.py)
def create_notification(conn, user_id, title, content, n_type='system'):
    conn.execute('INSERT INTO notifications (user_id, title, content, type) VALUES (?, ?, ?, ?)',
                (user_id, title, content, n_type))

def log_action(conn, user_id, action, details, ip_address):
    try:
        conn.execute('INSERT INTO system_logs (user_id, action, details, ip_address) VALUES (?, ?, ?, ?)',
                    (user_id, action, details, ip_address))
    except Exception as e:
        print(f"LOG ERROR: {e}")

@projects_bp.route('/projects', methods=['GET'])
@login_required
@swag_from({
    'tags': ['项目管理'],
    'summary': '获取项目列表',
    'description': '根据当前登录用户的角色，返回其有权限查看的项目列表。',
    'responses': {
        200: {'description': '获取成功'}
    }
})
def get_projects():
    user_id = session.get('user_id')
    role = session.get('role')
    
    conn = get_db_connection()
    query = '''
        SELECT p.*, c.title as competition_title, c.template_type as competition_template_type 
        FROM projects p
        LEFT JOIN competitions c ON p.competition_id = c.id
        WHERE 1=1
    '''
    params = []
    
    if role == ROLES['STUDENT']:
        query += " AND p.created_by = ?"
        params.append(user_id)
    elif role == ROLES['COLLEGE_APPROVER']:
        current_user = conn.execute('SELECT college FROM users WHERE id = ?', (user_id,)).fetchone()
        if current_user:
            query += " AND p.college = ?"
            params.append(current_user['college'])
    elif role == ROLES['SCHOOL_APPROVER']:
        # 学校管理员也能看全部或按需过滤
        pass
    elif role == ROLES['JUDGE']:
        query += " AND p.id IN (SELECT project_id FROM review_tasks WHERE judge_id = ?)"
        params.append(user_id)
    elif role == ROLES['TEACHER']:
        user = conn.execute('SELECT real_name FROM users WHERE id = ?', (user_id,)).fetchone()
        query += " AND p.advisor_name = ?"
        params.append(user['real_name'])
        
    query += f" AND p.id NOT IN ({','.join(map(str, GHOST_PROJECT_IDS))}) ORDER BY p.created_at DESC"
    
    projects = conn.execute(query, params).fetchall()
    
    results = []
    for row in projects:
        p = dict(row)
        if p.get('extra_info'):
            try:
                p['extra_info'] = json.loads(p['extra_info'])
            except:
                p['extra_info'] = {}
        else:
            p['extra_info'] = {}
            
        p['resolved_template_name'] = resolve_template_name(p)
        results.append(p)
    
    return success(data=results)

@projects_bp.route('/projects', methods=['POST'])
@login_required
@role_required([ROLES['STUDENT']])
@swag_from({
    'tags': ['项目管理'],
    'summary': '创建新项目申报',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'title': {'type': 'string'},
                    'project_type': {'type': 'string', 'enum': ['innovation', 'entrepreneurship']},
                    'advisor_name': {'type': 'string'}
                }
            }
        }
    ],
    'responses': {
        200: {'description': '创建成功'},
        400: {'description': '参数错误或不符合申报规则'}
    }
})
def create_project():
    user_id = session.get('user_id')
    data = request.json
    
    if data.get('id') and str(data.get('id')).isdigit() and int(data.get('id')) > 0:
         return fail('项目ID已存在，请刷新页面后重试', 400)

    conn = get_db_connection()
    try:
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        
        # 校验：项目名称不能重复 (优化建议)
        title = data.get('title')
        exist = conn.execute('SELECT id FROM projects WHERE title = ?', (title,)).fetchone()
        if exist:
            return fail('项目名称已存在', 400)
            
        # 校验：学生最多申报 2 个项目 (优化建议)
        count = conn.execute('SELECT COUNT(*) as count FROM projects WHERE created_by = ?', (user_id,)).fetchone()['count']
        if count >= 2:
            return fail('每个学生最多申报 2 个项目', 400)

        linked_project_id = data.get('linked_project_id')
        if linked_project_id is not None and linked_project_id != '':
            try:
                linked_project_id = int(linked_project_id)
            except Exception:
                return fail('关联大创项目ID无效', 400)
            if linked_project_id in GHOST_PROJECT_IDS:
                return fail('关联大创项目不存在', 400)
            linked = conn.execute(
                'SELECT id FROM projects WHERE id = ? AND created_by = ? AND template_type = ?',
                (linked_project_id, user_id, 'training')
            ).fetchone()
            if not linked:
                return fail('关联大创项目不存在或无权限', 400)
            data['linked_project_id'] = linked_project_id
        else:
            data['linked_project_id'] = None

        extra_info = data.get('extra_info', {})
        p_type = data.get('project_type')
        t_type = data.get('template_type', 'default')
        
        # --- 大挑 (Challenge Cup) 专属校验 ---
        if p_type == 'challenge_cup':
            # 1. 团队人数校验 (假设需要有团队成员，且不超过8人，具体根据实际情况)
            members = data.get('members', [])
            if len(members) > 8:
                return fail('大挑项目团队成员(含队长)不能超过8人', 400)
                
            # 2. 查重机制 (标题和核心摘要内容)
            abstract = data.get('abstract', '')
            if abstract:
                duplicate_content = conn.execute(
                    "SELECT id FROM projects WHERE project_type = 'challenge_cup' AND (title = ? OR (abstract != '' AND abstract LIKE ?))",
                    (title, f"%{abstract[:20]}%")
                ).fetchone()
                if duplicate_content:
                    return fail('项目标题或摘要前20字存在重复(查重未通过)，请勿重复申报', 400)

        extra_info_json = json.dumps(extra_info)
        
        if not t_type or t_type == 'default':
            t_type = 'innovation' if p_type == 'innovation' else 'startup'
            
        cursor = conn.execute('''
            INSERT INTO projects (
                title, leader_name, advisor_name, department, college, 
                project_type, template_type, level, status, year, created_by, abstract, assessment_indicators, competition_id, extra_info, inspiration_source, linked_project_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            title,
            data.get('leader_name', user['real_name']),
            data.get('advisor_name', ''),
            data.get('department', user['department']),
            data.get('college', user['college']),
            p_type,
            t_type,
            data.get('level', 'school'),
            data.get('year', datetime.now().year),
            user_id,
            data.get('abstract', ''),
            data.get('assessment_indicators', ''),
            data.get('competition_id'),
            extra_info_json,
            data.get('inspiration_source'),
            data.get('linked_project_id')
        ))
        project_id = cursor.lastrowid
        
        # 处理扩展表
        if t_type == 'innovation' or p_type == 'innovation':
            conn.execute('''
                INSERT INTO innovation_projects (project_id, background, content, innovation_point, expected_result, budget, schedule, project_source, risk_control)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (project_id, data.get('background'), data.get('content'), data.get('innovation_point'), data.get('expected_result'), data.get('budget'), data.get('schedule'), data.get('source'), data.get('risk_control')))
        else:
            conn.execute('''
                INSERT INTO entrepreneurship_projects (project_id, team_intro, market_prospect, operation_mode, financial_budget, risk_budget, investment_budget, project_source, tech_maturity, enterprise_mentor, innovation_content)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (project_id, data.get('team_intro'), data.get('market_prospect'), data.get('operation_mode'), data.get('financial_budget'), data.get('risk_budget'), data.get('investment_budget'), data.get('source'), data.get('tech_maturity'), data.get('enterprise_mentor'), data.get('innovation_content')))
            
        # 成员处理
        conn.execute('INSERT INTO project_members (project_id, is_leader, name, student_id, college, major, contact) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (project_id, True, user['real_name'], user['identity_number'], user['college'], data.get('major', ''), user['email'] or ''))
        
        for m in data.get('members', []):
            conn.execute('INSERT INTO project_members (project_id, is_leader, name, student_id, college, major, contact) VALUES (?, ?, ?, ?, ?, ?, ?)',
                        (project_id, False, m.get('name'), m.get('student_id'), m.get('college'), m.get('major'), m.get('contact')))
                        
        # 发送通知
        advisor_name = data.get('advisor_name', '').strip()
        if advisor_name:
            advisor = conn.execute('SELECT id FROM users WHERE real_name = ? AND role = ?', (advisor_name, ROLES['TEACHER'])).fetchone()
            if advisor:
                create_notification(conn, advisor['id'], '新项目指导申请', f"学生 {user['real_name']} 提交了新项目：{title}，请审核", 'approval')
        
        conn.commit()
        return success(data={'project_id': project_id}, message='提交成功')
    except Exception as e:
        conn.rollback()
        return fail(str(e), 500)

@projects_bp.route('/projects/<int:project_id>', methods=['GET'])
@login_required
def get_project_detail(project_id):
    conn = get_db_connection()
    project = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    if not project:
        return fail('项目不存在', 404)
        
    res = dict(project)
    if res.get('extra_info'):
        try:
            res['extra_info'] = json.loads(res['extra_info'])
        except:
            res['extra_info'] = {}
    
    # 扩展信息
    if res['project_type'] == 'innovation':
        extra = conn.execute('SELECT * FROM innovation_projects WHERE project_id = ?', (project_id,)).fetchone()
    else:
        extra = conn.execute('SELECT * FROM entrepreneurship_projects WHERE project_id = ?', (project_id,)).fetchone()
        
    if extra:
        extra_dict = dict(extra)
        if 'id' in extra_dict: del extra_dict['id']
        res.update(extra_dict)
        
    # 成员
    members = conn.execute('SELECT * FROM project_members WHERE project_id = ?', (project_id,)).fetchall()
    res['members'] = [dict(m) for m in members]
    
    # 评审记录
    reviews = conn.execute('''
        SELECT r.*, u.real_name as judge_name 
        FROM project_reviews r 
        JOIN users u ON r.judge_id = u.id 
        WHERE project_id = ?
    ''', (project_id,)).fetchall()
    res['reviews'] = [dict(r) for r in reviews]

    # 项目文件
    files = conn.execute('SELECT * FROM project_files WHERE project_id = ? ORDER BY created_at DESC', (project_id,)).fetchall()
    res['files'] = [dict(f) for f in files]
    
    # --- 大挑 (Challenge Cup) 盲审机制 ---
    user_role = session.get('role')
    if res['project_type'] == 'challenge_cup' and user_role == ROLES['JUDGE']:
        # 隐藏队长和成员信息
        res['leader_name'] = '***(盲审隐藏)'
        res['advisor_name'] = '***(盲审隐藏)'
        for member in res['members']:
            member['name'] = '***'
            member['student_id'] = '***'
            member['contact'] = '***'
        if 'leader_info' in res.get('extra_info', {}):
            res['extra_info']['leader_info']['name'] = '***'
            res['extra_info']['leader_info']['id'] = '***'
        if 'advisors' in res.get('extra_info', {}):
            for adv in res['extra_info']['advisors']:
                adv['name'] = '***'
                adv['phone'] = '***'
    
    return success(data=res)


def resolve_template_name(project_row):
    def row_get(r, k):
        if isinstance(r, dict):
            return r.get(k)
        try:
            return r[k]
        except Exception:
            return None

    key_map = {
        'challenge_cup': '大挑',
        'da_tiao': '大挑',
        'innovation_training': '大创创新训练',
        'training': '大创创新训练',
        'innovation': '大创创新训练',
        'internet_plus': '国创赛',
        'youth_challenge': '小挑',
        'xiao_tiao': '小挑',
        'entrepreneurship_training': '大创创业训练',
        'dachuang_entrepreneurship_training': '大创创业训练',
        'entrepreneurship_practice': '大创创业实践',
        'dachuang_entrepreneurship_practice': '大创创业实践',
        'three_creativity_regular': '三创赛常规赛',
        'sanchuang_regular': '三创赛常规赛',
        'three_creativity_practical': '三创赛实战赛',
        'sanchuang_practical': '三创赛实战赛'
    }

    comp_tpl = row_get(project_row, 'competition_template_type')
    comp_tpl_key = (str(comp_tpl).strip() if comp_tpl is not None else '')
    if comp_tpl_key and comp_tpl_key in key_map:
        return key_map[comp_tpl_key]

    title = (row_get(project_row, 'competition_title') or '').strip()
    if title:
        if '挑战杯' in title and '课外学术科技作品竞赛' in title:
            return '大挑'
        if '挑战杯' in title and '创业计划' in title:
            return '小挑'
        if '电子商务' in title and '实战赛' in title:
            return '三创赛实战赛'
        if '电子商务' in title and ('常规赛' in title or '挑战赛' in title):
            return '三创赛常规赛'
        if '创新大赛' in title or '互联网+' in title:
            return '国创赛'

    raw_keys = [
        row_get(project_row, 'template_type'),
        row_get(project_row, 'project_type')
    ]
    for k in raw_keys:
        kk = (str(k).strip() if k is not None else '')
        if kk and kk in key_map:
            return key_map[kk]

    if title:
        if '创新训练' in title:
            return '大创创新训练'
        if '创业训练' in title:
            return '大创创业训练'
        if '创业实践' in title:
            return '大创创业实践'

    return None


@projects_bp.route('/projects/<int:project_id>/process', methods=['GET'])
@login_required
def get_project_process(project_id):
    if project_id in GHOST_PROJECT_IDS:
        return fail('项目不存在', 404)

    conn = get_db_connection()
    project = conn.execute(
        '''
        SELECT
            p.id,
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
    if not project:
        return fail('项目不存在', 404)

    template_name = resolve_template_name(project)
    if not template_name:
        return success(data={
            'template_name': None,
            'process_structure': [],
            'has_mid_check': False,
            'has_final_acceptance': False,
            'node_status_options': {},
            'node_current_status': {},
            'node_comments': {},
            'award_levels': []
        })

    tpl = conn.execute(
        'SELECT id, template_name, process_structure, has_mid_check, has_final_acceptance FROM process_templates WHERE template_name = ?',
        (template_name,)
    ).fetchone()
    if not tpl:
        return fail('模板不存在', 404)

    try:
        process_structure = json.loads(tpl['process_structure'] or '[]')
    except Exception:
        process_structure = []

    nodes = conn.execute(
        'SELECT node_name, status_options FROM process_node_status WHERE template_id = ?',
        (tpl['id'],)
    ).fetchall()
    node_status_options = {}
    for n in nodes:
        try:
            node_status_options[n['node_name']] = json.loads(n['status_options'] or '[]')
        except Exception:
            node_status_options[n['node_name']] = []

    award = conn.execute(
        'SELECT level_options FROM award_levels WHERE template_id = ?',
        (tpl['id'],)
    ).fetchone()
    award_levels = []
    if award:
        try:
            award_levels = json.loads(award['level_options'] or '[]')
        except Exception:
            award_levels = []

    statuses = conn.execute(
        'SELECT node_name, current_status, comment, award_level FROM project_node_status WHERE project_id = ?',
        (project_id,)
    ).fetchall()
    node_current_status = {r['node_name']: r['current_status'] for r in statuses}
    node_comments = {r['node_name']: r['comment'] for r in statuses}
    node_award_levels = {r['node_name']: r['award_level'] for r in statuses}

    return success(data={
        'template_name': tpl['template_name'],
        'process_structure': process_structure,
        'has_mid_check': bool(tpl['has_mid_check']),
        'has_final_acceptance': bool(tpl['has_final_acceptance']),
        'node_status_options': node_status_options,
        'node_current_status': node_current_status,
        'node_comments': node_comments,
        'node_award_levels': node_award_levels,
        'award_levels': award_levels
    })

@projects_bp.route('/projects/<int:project_id>/process', methods=['PUT'])
@login_required
def update_project_process(project_id):
    if project_id in GHOST_PROJECT_IDS:
        return fail('项目不存在', 404)

    role = session.get('role')
    if role == ROLES['STUDENT']:
        return fail('无权限', 403)

    data = request.json or {}
    node_name = (data.get('node_name') or '').strip()
    current_status = (data.get('current_status') or '').strip()
    comment = (data.get('comment') or '').strip()
    award_level = (data.get('award_level') or '').strip()
    
    if not node_name:
        return fail('参数错误', 400)

    conn = get_db_connection()
    project = conn.execute(
        '''
        SELECT
            p.id,
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
    if not project:
        return fail('项目不存在', 404)

    template_name = resolve_template_name(project)
    if not template_name:
        return fail('项目未绑定流程模板', 400)

    if template_name == '大挑':
        if node_name == '学院赛' and role not in [ROLES['COLLEGE_APPROVER'], ROLES['PROJECT_ADMIN'], ROLES['SYSTEM_ADMIN']]:
            return fail('无权限', 403)
        if node_name in ['校赛', '省赛', '国赛'] and role not in [ROLES['SCHOOL_APPROVER'], ROLES['PROJECT_ADMIN'], ROLES['SYSTEM_ADMIN']]:
            return fail('无权限', 403)

    tpl = conn.execute(
        'SELECT id, process_structure FROM process_templates WHERE template_name = ?',
        (template_name,)
    ).fetchone()
    if not tpl:
        return fail('模板不存在', 404)

    try:
        process_structure = json.loads(tpl['process_structure'] or '[]')
    except Exception:
        process_structure = []

    if node_name not in process_structure:
        return fail('节点不存在', 400)

    opt_row = conn.execute(
        'SELECT status_options FROM process_node_status WHERE template_id = ? AND node_name = ?',
        (tpl['id'], node_name)
    ).fetchone()
    if opt_row:
        try:
            options = json.loads(opt_row['status_options'] or '[]')
        except Exception:
            options = []
        if options and current_status not in options:
            return fail('状态值不合法', 400)

    prev = conn.execute(
        'SELECT current_status, comment, award_level FROM project_node_status WHERE project_id = ? AND node_name = ?',
        (project_id, node_name)
    ).fetchone()
    prev_status = prev['current_status'] if prev else None
    prev_comment = prev['comment'] if prev else ''
    prev_award_level = prev['award_level'] if prev else ''

    if template_name == '大挑' and node_name in ['学院赛', '校赛'] and prev_status == '已推荐':
        if current_status == prev_status and comment == (prev_comment or '') and award_level == (prev_award_level or ''):
            return success(message='保存成功')
        return fail(f'{node_name}已通过，不能修改', 400)

    conn.execute(
        'INSERT OR REPLACE INTO project_node_status (project_id, node_name, current_status, comment, award_level, updated_by, updated_at) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)',
        (project_id, node_name, current_status, comment, award_level, session.get('user_id'))
    )

    if template_name == '大挑' and node_name == '学院赛' and current_status == '已推荐':
        p_row = conn.execute(
            'SELECT id, title, created_by, college, status, current_level, extra_info FROM projects WHERE id = ?',
            (project_id,)
        ).fetchone()
        if p_row:
            conn.execute(
                'UPDATE projects SET current_level = ?, review_stage = ?, college_review_result = ? WHERE id = ?',
                ('school', 'school', 'approved', project_id)
            )
            if p_row['status'] == 'pending':
                conn.execute('UPDATE projects SET status = ? WHERE id = ?', ('under_review', project_id))

        next_node = '校赛'
        exists_next = conn.execute(
            'SELECT id FROM project_node_status WHERE project_id = ? AND node_name = ?',
            (project_id, next_node)
        ).fetchone()
        if not exists_next:
            conn.execute(
                'INSERT INTO project_node_status (project_id, node_name, current_status, comment, award_level, updated_by, updated_at) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)',
                (project_id, next_node, '待评审', '', '', session.get('user_id'))
            )

        discipline_group = '理工组'
        try:
            ei = json.loads(p_row['extra_info'] or '{}')
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

            for m in members:
                conn.execute(
                    'INSERT INTO notifications (user_id, title, content, type) VALUES (?, ?, ?, ?)',
                    (m['user_id'], '新增校赛评审任务', f'项目《{p_row["title"]}》已进入校赛，请在“我的评审任务”中完成评审。', 'project')
                )

        conn.execute(
            'INSERT INTO notifications (user_id, title, content, type) VALUES (?, ?, ?, ?)',
            (p_row['created_by'], '学院赛已推荐至校赛', f'你的项目《{p_row["title"]}》已由学院推荐进入校赛评审阶段。', 'project')
        )

        school_admins = conn.execute(
            'SELECT id FROM users WHERE role IN (?, ?, ?)',
            (ROLES['SCHOOL_APPROVER'], ROLES['PROJECT_ADMIN'], ROLES['SYSTEM_ADMIN'])
        ).fetchall()
        for u in school_admins:
            conn.execute(
                'INSERT INTO notifications (user_id, title, content, type) VALUES (?, ?, ?, ?)',
                (u['id'], '项目进入校赛评审池', f'项目《{p_row["title"]}》已从学院赛推荐进入校赛评审池。', 'approval')
            )

    if template_name == '大挑' and node_name == '校赛' and current_status == '已推荐':
        p_row = conn.execute(
            'SELECT id, title, created_by, status FROM projects WHERE id = ?',
            (project_id,)
        ).fetchone()
        if p_row:
            conn.execute(
                'UPDATE projects SET current_level = ?, review_stage = ?, school_review_result = ? WHERE id = ?',
                ('provincial', 'provincial', 'approved', project_id)
            )

            next_node = '省赛'
            exists_next = conn.execute(
                'SELECT id FROM project_node_status WHERE project_id = ? AND node_name = ?',
                (project_id, next_node)
            ).fetchone()
            if not exists_next:
                conn.execute(
                    'INSERT INTO project_node_status (project_id, node_name, current_status, comment, award_level, updated_by, updated_at) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)',
                    (project_id, next_node, '待评审', '', '', session.get('user_id'))
                )

            conn.execute(
                'INSERT INTO notifications (user_id, title, content, type) VALUES (?, ?, ?, ?)',
                (p_row['created_by'], '校赛已推荐至省赛', f'你的项目《{p_row["title"]}》已由学校推荐进入省赛阶段（系统内仅做结果录入）。', 'project')
            )
    conn.commit()
    return success(message='保存成功')



@projects_bp.route('/projects/<int:project_id>/midterm', methods=['POST'])
@login_required
@role_required([ROLES['STUDENT']])
def submit_midterm(project_id):
    if project_id in GHOST_PROJECT_IDS:
        return fail('项目不存在', 404)

    user_id = session.get('user_id')
    conn = get_db_connection()
    project = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    if not project:
        return fail('项目不存在', 404)
    if project['created_by'] != user_id:
        return fail('无权限', 403)

    row_for_tpl = dict(project)
    comp_id = project['competition_id'] if 'competition_id' in project.keys() else None
    if comp_id:
        comp = conn.execute('SELECT template_type, title FROM competitions WHERE id = ?', (comp_id,)).fetchone()
        if comp:
            row_for_tpl['competition_template_type'] = comp['template_type']
            row_for_tpl['competition_title'] = comp['title']
    tpl_name = resolve_template_name(row_for_tpl)
    tpl = conn.execute('SELECT has_mid_check FROM process_templates WHERE template_name = ?', (tpl_name,)).fetchone() if tpl_name else None
    if not tpl or not tpl['has_mid_check']:
        return fail('当前模板不支持中期检查', 400)

    if project['status'] not in ['rated', 'midterm_rejected', 'midterm_submitted']:
        return fail('当前状态无法提交中期材料', 400)

    data = request.json or {}
    attachments = data.get('attachments', {}) or {}

    try:
        info = json.loads(project['extra_info']) if project['extra_info'] else {}
    except Exception:
        info = {}

    if 'process_materials' not in info:
        info['process_materials'] = {}
    info['process_materials']['midterm'] = attachments
    info['process_materials']['midterm_submitted_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    for _, url in attachments.items():
        if url:
            existing = conn.execute(
                'SELECT id FROM project_files WHERE project_id = ? AND file_type = ? AND file_path = ?',
                (project_id, 'midterm', url)
            ).fetchone()
            if not existing:
                filename = str(url).split('/')[-1]
                conn.execute(
                    "INSERT INTO project_files (project_id, file_type, file_path, original_filename, status) VALUES (?, 'midterm', ?, ?, 'pending')",
                    (project_id, url, filename)
                )
            else:
                conn.execute('UPDATE project_files SET status = ? WHERE id = ?', ('pending', existing['id']))

    conn.execute('UPDATE projects SET status = ?, extra_info = ? WHERE id = ?', ('midterm_submitted', json.dumps(info, ensure_ascii=False), project_id))

    create_notification(conn, user_id, '中期材料提交成功', f"项目 {project['title']} 的中期材料已提交", 'system')
    advisor_name = (project['advisor_name'] or '').strip()
    if advisor_name:
        advisor = conn.execute('SELECT id FROM users WHERE real_name = ? AND role = ?', (advisor_name, ROLES['TEACHER'])).fetchone()
        if advisor:
            create_notification(conn, advisor['id'], '中期材料待审核', f"项目 {project['title']} 提交了中期材料，请审核", 'approval')

    approvers = conn.execute('SELECT id FROM users WHERE role = ? AND college = ?', (ROLES['COLLEGE_APPROVER'], project['college'])).fetchall()
    for approver in approvers:
        create_notification(conn, approver['id'], '中期材料待审核', f"项目 {project['title']} 提交了中期材料，请审核", 'approval')

    conn.commit()
    return success(message='中期材料提交成功')


@projects_bp.route('/projects/<int:project_id>/conclusion', methods=['POST'])
@login_required
@role_required([ROLES['STUDENT']])
def submit_conclusion(project_id):
    if project_id in GHOST_PROJECT_IDS:
        return fail('项目不存在', 404)

    user_id = session.get('user_id')
    conn = get_db_connection()
    project = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    if not project:
        return fail('项目不存在', 404)
    if project['created_by'] != user_id:
        return fail('无权限', 403)

    row_for_tpl = dict(project)
    comp_id = project['competition_id'] if 'competition_id' in project.keys() else None
    if comp_id:
        comp = conn.execute('SELECT template_type, title FROM competitions WHERE id = ?', (comp_id,)).fetchone()
        if comp:
            row_for_tpl['competition_template_type'] = comp['template_type']
            row_for_tpl['competition_title'] = comp['title']
    tpl_name = resolve_template_name(row_for_tpl)
    tpl = conn.execute('SELECT has_final_acceptance FROM process_templates WHERE template_name = ?', (tpl_name,)).fetchone() if tpl_name else None
    if not tpl or not tpl['has_final_acceptance']:
        return fail('当前模板不支持结题验收', 400)

    if project['status'] not in ['midterm_approved', 'conclusion_rejected', 'conclusion_submitted']:
        return fail('当前状态无法提交结题材料', 400)

    data = request.json or {}
    attachments = data.get('attachments', {}) or {}

    try:
        info = json.loads(project['extra_info']) if project['extra_info'] else {}
    except Exception:
        info = {}

    if 'process_materials' not in info:
        info['process_materials'] = {}
    info['process_materials']['conclusion'] = attachments
    info['process_materials']['conclusion_submitted_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    for _, url in attachments.items():
        if url:
            existing = conn.execute(
                'SELECT id FROM project_files WHERE project_id = ? AND file_type = ? AND file_path = ?',
                (project_id, 'conclusion', url)
            ).fetchone()
            if not existing:
                filename = str(url).split('/')[-1]
                conn.execute(
                    "INSERT INTO project_files (project_id, file_type, file_path, original_filename, status) VALUES (?, 'conclusion', ?, ?, 'pending')",
                    (project_id, url, filename)
                )
            else:
                conn.execute('UPDATE project_files SET status = ? WHERE id = ?', ('pending', existing['id']))

    conn.execute('UPDATE projects SET status = ?, extra_info = ? WHERE id = ?', ('conclusion_submitted', json.dumps(info, ensure_ascii=False), project_id))

    create_notification(conn, user_id, '结题材料提交成功', f"项目 {project['title']} 的结题材料已提交", 'system')
    advisor_name = (project['advisor_name'] or '').strip()
    if advisor_name:
        advisor = conn.execute('SELECT id FROM users WHERE real_name = ? AND role = ?', (advisor_name, ROLES['TEACHER'])).fetchone()
        if advisor:
            create_notification(conn, advisor['id'], '结题材料待审核', f"项目 {project['title']} 提交了结题材料，请审核", 'approval')

    conn.commit()
    return success(message='结题材料提交成功')

@projects_bp.route('/projects/<int:project_id>', methods=['PUT'])
@login_required
def update_project(project_id):
    user_id = session.get('user_id')
    role = session.get('role')
    
    # Allow students and approvers to edit
    allowed_roles = [ROLES['STUDENT'], ROLES['COLLEGE_APPROVER'], ROLES['SCHOOL_APPROVER'], ROLES['PROJECT_ADMIN']]
    if role not in allowed_roles:
        return fail('无权限', 403)

    conn = get_db_connection()
    project = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    if not project:
        return fail('项目不存在', 404)
        
    data = request.json
    extra_info = data.get('extra_info', {})
    
    # --- 大挑 (Challenge Cup) 专属校验 ---
    p_type = data.get('project_type') or project['project_type']
    if p_type == 'challenge_cup':
        # 1. 团队人数校验
        members = data.get('members', [])
        if len(members) > 8:
            return fail('大挑项目团队成员(含队长)不能超过8人', 400)
            
        # 2. 查重机制 (标题和核心摘要内容)
        abstract = data.get('abstract', '')
        title = data.get('title')
        if abstract:
            duplicate_content = conn.execute(
                "SELECT id FROM projects WHERE project_type = 'challenge_cup' AND id != ? AND (title = ? OR (abstract != '' AND abstract LIKE ?))",
                (project_id, title, f"%{abstract[:20]}%")
            ).fetchone()
            if duplicate_content:
                return fail('项目标题或摘要前20字存在重复(查重未通过)，请勿重复申报', 400)

    extra_info_json = json.dumps(extra_info)

    # Permission checks
    if role == ROLES['STUDENT']:
        is_owner = (project['created_by'] == user_id)
        if not is_owner:
            user_info = conn.execute('SELECT identity_number, real_name FROM users WHERE id = ?', (user_id,)).fetchone()
            is_leader = False
            
            if user_info and user_info['identity_number']:
                member_leader = conn.execute('SELECT * FROM project_members WHERE project_id = ? AND is_leader = 1 AND student_id = ?', (project_id, user_info['identity_number'])).fetchone()
                if member_leader: is_leader = True
                else:
                    all_leaders = conn.execute('SELECT * FROM project_members WHERE project_id = ? AND is_leader = 1', (project_id,)).fetchall()
                    for l in all_leaders:
                        if l['student_id'] and l['student_id'].strip() == user_info['identity_number'].strip():
                            is_leader = True
                            break
            if not is_leader and user_info and user_info['real_name']:
                 member_leader = conn.execute('SELECT * FROM project_members WHERE project_id = ? AND is_leader = 1 AND name = ?', (project_id, user_info['real_name'])).fetchone()
                 if member_leader: 
                     is_leader = True
                 else:
                     all_leaders = conn.execute('SELECT * FROM project_members WHERE project_id = ? AND is_leader = 1', (project_id,)).fetchall()
                     for l in all_leaders:
                         if l['name'] and user_info['real_name'] in l['name']:
                             is_leader = True
                             break

            if not is_leader:
                return fail('只能修改自己的项目', 403)
            
        if project['status'] not in ['pending', 'rejected', 'advisor_approved', 'college_approved']:
            return fail('当前状态无法修改', 400)
    
    try:
        new_status = project['status']
        if role == ROLES['STUDENT']:
            new_status = 'pending'
            if project['status'] == 'school_approved':
                new_status = 'school_approved'
        
        conn.execute('''
            UPDATE projects SET 
                title=?, leader_name=?, advisor_name=?, department=?, college=?,
                project_type=?, level=?, year=?, abstract=?, assessment_indicators=?,
                extra_info=?, status=?
            WHERE id=?
        ''', (
            data.get('title'),
            data.get('leader_name'),
            data.get('advisor_name'),
            data.get('department'),
            data.get('college'),
            data.get('project_type'),
            data.get('level'),
            data.get('year'),
            data.get('abstract'),
            data.get('assessment_indicators'),
            extra_info_json,
            new_status,
            project_id
        ))
        
        if data.get('project_type') == 'innovation':
             conn.execute('''
                UPDATE innovation_projects SET 
                    background=?, content=?, innovation_point=?, expected_result=?, 
                    budget=?, schedule=?, project_source=?, risk_control=?
                WHERE project_id=?
            ''', (
                data.get('background'), data.get('content'), data.get('innovation_point'), 
                data.get('expected_result'), data.get('budget'), data.get('schedule'), 
                data.get('source'), data.get('risk_control'), 
                project_id
            ))
        else:
             conn.execute('''
                UPDATE entrepreneurship_projects SET 
                    team_intro=?, market_prospect=?, operation_mode=?, financial_budget=?, 
                    risk_budget=?, investment_budget=?, project_source=?, tech_maturity=?, 
                    enterprise_mentor=?, innovation_content=?
                WHERE project_id=?
            ''', (
                data.get('team_intro'), data.get('market_prospect'), data.get('operation_mode'), 
                data.get('financial_budget'), data.get('risk_budget'), data.get('investment_budget'), 
                data.get('source'), data.get('tech_maturity'), data.get('enterprise_mentor'), 
                data.get('innovation_content'), 
                project_id
            ))
            
        current_leader_member = conn.execute('SELECT * FROM project_members WHERE project_id=? AND is_leader=1', (project_id,)).fetchone()
        conn.execute('DELETE FROM project_members WHERE project_id=?', (project_id,))
        
        leader_info = data.get('extra_info', {}).get('leader_info', {})
        
        leader_name = data.get('leader_name') or leader_info.get('name')
        if not leader_name and current_leader_member: leader_name = current_leader_member['name']
        if not leader_name: leader_name = project['leader_name']

        leader_id = data.get('leader_id') or data.get('student_id') or leader_info.get('id')
        if not leader_id and current_leader_member: leader_id = current_leader_member['student_id']

        leader_college = data.get('college') or leader_info.get('college')
        if not leader_college and current_leader_member: leader_college = current_leader_member['college']

        leader_major = data.get('major') or leader_info.get('major')
        if not leader_major and current_leader_member: leader_major = current_leader_member['major']
        
        leader_contact = data.get('contact') or data.get('email') or data.get('phone') or leader_info.get('email') or leader_info.get('phone') or ''
        if not leader_contact and current_leader_member: leader_contact = current_leader_member['contact']
        
        if not leader_contact:
             u = conn.execute('SELECT email FROM users WHERE id=?', (user_id,)).fetchone()
             if u and u['email']: leader_contact = u['email']

        conn.execute('''
            INSERT INTO project_members (
                project_id, is_leader, name, student_id, college, major, contact
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            project_id, True, leader_name, leader_id, leader_college, leader_major, leader_contact
        ))
        for m in data.get('members', []):
            if m.get('student_id') and str(m.get('student_id')) == str(leader_id):
                continue
            conn.execute('INSERT INTO project_members (project_id, is_leader, name, student_id, college, major, contact) VALUES (?, ?, ?, ?, ?, ?, ?)',
                        (project_id, False, m.get('name'), m.get('student_id'), m.get('college'), m.get('major'), m.get('contact')))
                        
        conn.commit()
        return success(message='修改成功')
    except Exception as e:
        conn.rollback()
        return fail(str(e), 500)

@projects_bp.route('/projects/<int:project_id>/status', methods=['PUT'])
@login_required
@role_required([ROLES['COLLEGE_APPROVER'], ROLES['SCHOOL_APPROVER'], ROLES['PROJECT_ADMIN']])
def update_project_status(project_id):
    # 优化建议：状态更新接口
    data = request.json
    new_status = data.get('status')
    feedback = data.get('feedback', '')
    
    role = session['role']
    allowed_status = {
        ROLES['COLLEGE_APPROVER']: ['college_approved', 'rejected'],
        ROLES['SCHOOL_APPROVER']: ['school_approved', 'rated', 'rejected', 'finished'],
        ROLES['PROJECT_ADMIN']: ['pending', 'college_approved', 'school_approved', 'rated', 'rejected', 'finished']
    }
    
    if new_status not in allowed_status.get(role, []):
        return fail('不允许设置该状态', 403)
        
    conn = get_db_connection()
    project = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    if not project:
        return fail('项目不存在', 404)
        
    try:
        if role == ROLES['COLLEGE_APPROVER']:
            conn.execute('UPDATE projects SET status = ?, college_feedback = ? WHERE id = ?', (new_status, feedback, project_id))
        else:
            conn.execute('UPDATE projects SET status = ?, school_feedback = ? WHERE id = ?', (new_status, feedback, project_id))
            
        create_notification(conn, project['created_by'], '项目状态更新', f'您的项目 {project["title"]} 状态已被更新为 {new_status}')
        conn.commit()
        return success(message='状态更新成功')
    except Exception as e:
        conn.rollback()
        return fail(str(e), 500)

@projects_bp.route('/projects/<int:project_id>/review', methods=['POST'])
@login_required
@role_required([ROLES['JUDGE']])
def review_project(project_id):
    user_id = session['user_id']
    data = request.json
    score = data.get('score')
    comment = data.get('comment', '').strip()
    criteria_scores = data.get('criteria_scores', {})
    
    conn = get_db_connection()
    try:
        project = conn.execute('SELECT project_type FROM projects WHERE id = ?', (project_id,)).fetchone()
        if not project:
            return fail('项目不存在', 404)
            
        # 大挑专属多维度打分校验
        if project['project_type'] == 'challenge_cup':
            for score_key in ['score_innovation', 'score_feasibility', 'score_value']:
                sub_score = criteria_scores.get(score_key, 0)
                try:
                    sub_score_int = int(sub_score)
                    if not (1 <= sub_score_int <= 10):
                        return fail(f'{score_key} 评分需为1-10分', 400)
                except ValueError:
                    return fail(f'{score_key} 评分格式错误', 400)
            
            # 自动计算总分 (如果前端没传)
            if score is None:
                score = sum(int(criteria_scores.get(k, 0)) for k in ['score_innovation', 'score_feasibility', 'score_value']) * 3.33 # Scale to 100 roughly, or just use as is.

        try:
            score_int = int(score)
        except:
            return fail('评分必须为整数', 400)
            
        if score_int < 0 or score_int > 100:
            return fail('总评分必须在 0-100 之间', 400)
            
        conn.execute('''
            INSERT INTO project_reviews (project_id, judge_id, score, comment, criteria_scores)
            VALUES (?, ?, ?, ?, ?)
        ''', (project_id, user_id, score_int, comment, json.dumps(criteria_scores)))
        
        # 更新任务状态
        conn.execute('UPDATE review_tasks SET status = "completed" WHERE project_id = ? AND judge_id = ?', (project_id, user_id))
        
        log_action(conn, user_id, 'REVIEW', f'Reviewed Project {project_id}', request.remote_addr)
        conn.commit()
        return success(message='评审提交成功')
    except Exception as e:
        conn.rollback()
        return fail(str(e), 500)

@projects_bp.route('/projects/<int:pid>/upload', methods=['POST'])
@login_required
def upload_project_file(pid):
    # 优化建议：文件上传接口
    if 'file' not in request.files:
        return fail('请选择上传文件', 400)
        
    file = request.files['file']
    if file.filename == '':
        return fail('文件名不能为空', 400)
        
    file_type = request.form.get('file_type', 'midterm')
    
    filename = secure_filename(file.filename)
    ts = int(datetime.now().timestamp())
    save_filename = f"project_{pid}_{file_type}_{ts}_{filename}"
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], save_filename)
    
    try:
        file.save(file_path)
        url = f"/static/uploads/{save_filename}"
        
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO project_files (project_id, file_type, file_path, original_filename, status)
            VALUES (?, ?, ?, ?, 'pending')
        ''', (pid, file_type, url, filename))
        
        # 更新项目状态
        new_status = 'midterm_submitted' if file_type == 'midterm' else 'conclusion_submitted'
        conn.execute('UPDATE projects SET status = ? WHERE id = ?', (new_status, pid))
        
        conn.commit()
        return success(data={'url': url}, message='文件上传成功')
    except Exception as e:
        return fail(str(e), 500)


def normalize_level(v):
    s = (v or '').strip().lower()
    if s in ['school', '校级', '院级']:
        return 'school'
    if s in ['provincial', 'province', '省级']:
        return 'provincial'
    if s in ['national', 'country', '国家级']:
        return 'national'
    return s or 'school'


def level_display(v):
    s = normalize_level(v)
    return '校级' if s == 'school' else ('省级' if s == 'provincial' else ('国家级' if s == 'national' else v))


@projects_bp.route('/my/dachuang-projects', methods=['GET'])
@login_required
@role_required([ROLES['STUDENT']])
def get_my_dachuang_projects():
    user_id = session.get('user_id')
    conn = get_db_connection()
    rows = conn.execute(
        f'''
        SELECT id, title, status, level, created_at
        FROM projects
        WHERE created_by = ?
          AND template_type = 'training'
          AND id NOT IN ({','.join(map(str, GHOST_PROJECT_IDS))})
        ORDER BY created_at DESC
        ''',
        (user_id,)
    ).fetchall()
    return success(data=[dict(r) for r in rows])


@projects_bp.route('/projects/<int:project_id>/upgrade-requests', methods=['GET'])
@login_required
def get_upgrade_requests(project_id):
    user_id = session.get('user_id')
    role = session.get('role')
    conn = get_db_connection()
    project = conn.execute('SELECT id, created_by FROM projects WHERE id = ?', (project_id,)).fetchone()
    if not project:
        return fail('项目不存在', 404)

    if role == ROLES['STUDENT'] and project['created_by'] != user_id:
        return fail('无权限', 403)

    rows = conn.execute(
        '''
        SELECT r.*, u.real_name AS applicant_name, ru.real_name AS reviewer_name
        FROM project_upgrade_requests r
        LEFT JOIN users u ON r.applicant_id = u.id
        LEFT JOIN users ru ON r.reviewer_id = ru.id
        WHERE r.project_id = ?
        ORDER BY r.created_at DESC
        ''',
        (project_id,)
    ).fetchall()
    return success(data=[dict(r) for r in rows])


@projects_bp.route('/projects/<int:project_id>/upgrade-requests', methods=['POST'])
@login_required
@role_required([ROLES['STUDENT']])
def create_upgrade_request(project_id):
    user_id = session.get('user_id')
    data = request.json or {}
    to_level = normalize_level(data.get('to_level'))
    reason = (data.get('reason') or '').strip()

    if to_level not in ['provincial', 'national']:
        return fail('升级目标无效', 400)

    conn = get_db_connection()
    project = conn.execute('SELECT id, title, created_by, level, status, template_type FROM projects WHERE id = ?', (project_id,)).fetchone()
    if not project:
        return fail('项目不存在', 404)
    if project['created_by'] != user_id:
        return fail('无权限', 403)
    if project['template_type'] != 'training':
        return fail('仅大创项目支持升级申请', 400)

    from_level = normalize_level(project['level'])
    if from_level not in ['school', 'provincial']:
        return fail('当前项目级别不支持升级', 400)
    if from_level == 'provincial' and to_level != 'national':
        return fail('省级项目仅可申请升级为国家级', 400)

    ok_status = set(['school_approved', 'rated', 'midterm_submitted', 'midterm_approved', 'conclusion_submitted', 'finished'])
    if (project['status'] or '') not in ok_status:
        return fail('项目未立项或当前状态不允许升级申请', 400)

    existing = conn.execute(
        'SELECT id FROM project_upgrade_requests WHERE project_id = ? AND status = ?',
        (project_id, 'pending')
    ).fetchone()
    if existing:
        return fail('已有待处理的升级申请', 400)

    try:
        conn.execute(
            '''
            INSERT INTO project_upgrade_requests (project_id, applicant_id, from_level, to_level, reason)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (project_id, user_id, from_level, to_level, reason)
        )

        reviewers = conn.execute(
            'SELECT id FROM users WHERE role IN (?, ?, ?)',
            (ROLES['PROJECT_ADMIN'], ROLES['SCHOOL_APPROVER'], ROLES['JUDGE'])
        ).fetchall()
        for r in reviewers:
            create_notification(conn, r['id'], '大创项目升级申请', f'项目《{project["title"]}》提交了升级申请（{level_display(from_level)}→{level_display(to_level)}）', 'approval')

        log_action(conn, user_id, 'UPGRADE_REQUEST', f'Project {project_id} {from_level}->{to_level}', request.remote_addr)
        conn.commit()
        return success(message='升级申请已提交')
    except Exception as e:
        conn.rollback()
        return fail(str(e), 500)


@projects_bp.route('/upgrade-requests', methods=['GET'])
@login_required
@role_required([ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN'], ROLES['SCHOOL_APPROVER'], ROLES['JUDGE']])
def list_upgrade_requests():
    status = (request.args.get('status') or '').strip()
    params = []
    where = 'WHERE 1=1'
    if status:
        where += ' AND r.status = ?'
        params.append(status)

    conn = get_db_connection()
    rows = conn.execute(
        f'''
        SELECT r.*, p.title AS project_title, u.real_name AS applicant_name, ru.real_name AS reviewer_name
        FROM project_upgrade_requests r
        JOIN projects p ON r.project_id = p.id
        LEFT JOIN users u ON r.applicant_id = u.id
        LEFT JOIN users ru ON r.reviewer_id = ru.id
        {where}
        ORDER BY r.created_at DESC
        ''',
        params
    ).fetchall()
    return success(data=[dict(r) for r in rows])


@projects_bp.route('/upgrade-requests/<int:rid>/review', methods=['PUT'])
@login_required
@role_required([ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN'], ROLES['SCHOOL_APPROVER'], ROLES['JUDGE']])
def review_upgrade_request(rid):
    reviewer_id = session.get('user_id')
    data = request.json or {}
    status = (data.get('status') or '').strip().lower()
    comment = (data.get('comment') or '').strip()

    if status not in ['approved', 'rejected']:
        return fail('状态无效', 400)

    conn = get_db_connection()
    req_row = conn.execute('SELECT * FROM project_upgrade_requests WHERE id = ?', (rid,)).fetchone()
    if not req_row:
        return fail('升级申请不存在', 404)
    if req_row['status'] != 'pending':
        return fail('升级申请已处理', 400)

    project = conn.execute('SELECT id, title, level, created_by FROM projects WHERE id = ?', (req_row['project_id'],)).fetchone()
    if not project:
        return fail('项目不存在', 404)

    try:
        now = datetime.now().isoformat(sep=' ', timespec='seconds')
        conn.execute(
            '''
            UPDATE project_upgrade_requests
            SET status = ?, reviewer_id = ?, review_comment = ?, reviewed_at = ?
            WHERE id = ?
            ''',
            (status, reviewer_id, comment, now, rid)
        )

        if status == 'approved':
            conn.execute('UPDATE projects SET level = ? WHERE id = ?', (req_row['to_level'], project['id']))

        create_notification(
            conn,
            req_row['applicant_id'],
            '大创项目升级结果',
            f'项目《{project["title"]}》升级申请结果：{"通过" if status == "approved" else "驳回"}（{level_display(req_row["from_level"])}→{level_display(req_row["to_level"])})',
            'system'
        )

        log_action(conn, reviewer_id, 'UPGRADE_REVIEW', f'Request {rid} {status}', request.remote_addr)
        conn.commit()
        return success(message='处理成功')
    except Exception as e:
        conn.rollback()
        return fail(str(e), 500)


def normalize_review_stage(v):
    s = (v or '').strip().lower()
    if s in ['校赛', 'school']:
        return 'school'
    if s in ['省赛', 'provincial', 'province']:
        return 'provincial'
    if s in ['国赛', 'national', 'country']:
        return 'national'
    return s


def normalize_review_result(v):
    s = (v or '').strip().lower()
    if s in ['通过', 'approved', 'pass']:
        return 'approved'
    if s in ['不通过', 'rejected', 'fail']:
        return 'rejected'
    if s in ['待评审', 'pending']:
        return 'pending'
    return s


def normalize_award_level(v):
    s = (v or '').strip().lower()
    if s in ['金奖', 'gold']:
        return 'gold'
    if s in ['银奖', 'silver']:
        return 'silver'
    if s in ['铜奖', 'bronze']:
        return 'bronze'
    if s in ['特等', 'special']:
        return 'special'
    if s in ['一等', 'first']:
        return 'first'
    if s in ['二等', 'second']:
        return 'second'
    if s in ['三等', 'third']:
        return 'third'
    if s in ['优秀奖', 'excellent']:
        return 'excellent'
    if s in ['无', 'none']:
        return 'none'
    return s


def can_view_project(conn, role, user_id, project_row):
    if role == ROLES['STUDENT']:
        return project_row['created_by'] == user_id
    if role == ROLES['COLLEGE_APPROVER']:
        cur = conn.execute('SELECT college FROM users WHERE id = ?', (user_id,)).fetchone()
        return bool(cur) and project_row.get('college') == cur['college']
    return True


@projects_bp.route('/projects/<int:project_id>/admin-review', methods=['GET'])
@login_required
@role_required([ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN'], ROLES['COLLEGE_APPROVER'], ROLES['SCHOOL_APPROVER'], ROLES['JUDGE']])
def get_admin_review(project_id):
    if project_id in GHOST_PROJECT_IDS:
        return fail('项目不存在', 404)

    user_id = session.get('user_id')
    role = session.get('role')
    conn = get_db_connection()
    project = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    if not project:
        return fail('项目不存在', 404)
    if not can_view_project(conn, role, user_id, dict(project)):
        return fail('无权限', 403)

    data = {
        'review_stage': project['review_stage'],
        'college_review_result': project['college_review_result'],
        'school_review_result': project['school_review_result'],
        'provincial_award_level': project['provincial_award_level'],
        'national_award_level': project['national_award_level'],
        'research_admin_opinion': project['research_admin_opinion'],
        'department_head_opinion': project['department_head_opinion']
    }
    return success(data=data)


@projects_bp.route('/projects/<int:project_id>/admin-review', methods=['PUT'])
@login_required
@role_required([ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN'], ROLES['COLLEGE_APPROVER'], ROLES['SCHOOL_APPROVER'], ROLES['JUDGE']])
def update_admin_review(project_id):
    if project_id in GHOST_PROJECT_IDS:
        return fail('项目不存在', 404)

    user_id = session.get('user_id')
    role = session.get('role')
    data = request.json or {}

    conn = get_db_connection()
    project = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    if not project:
        return fail('项目不存在', 404)
    if not can_view_project(conn, role, user_id, dict(project)):
        return fail('无权限', 403)

    row_for_tpl = dict(project)
    comp_id = project['competition_id'] if 'competition_id' in project.keys() else None
    if comp_id:
        comp = conn.execute('SELECT template_type, title FROM competitions WHERE id = ?', (comp_id,)).fetchone()
        if comp:
            row_for_tpl['competition_template_type'] = comp['template_type']
            row_for_tpl['competition_title'] = comp['title']
    template_name = resolve_template_name(row_for_tpl)
    if template_name == '大挑' and (project['college_review_result'] == 'approved'):
        if 'college_review_result' in data or 'department_head_opinion' in data:
            return fail('学院赛已通过，相关信息不可修改', 400)

    editable = set()
    if role in [ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN']]:
        editable = {
            'review_stage',
            'college_review_result',
            'school_review_result',
            'provincial_award_level',
            'national_award_level',
            'research_admin_opinion',
            'department_head_opinion'
        }
    elif role == ROLES['COLLEGE_APPROVER']:
        editable = {'college_review_result', 'department_head_opinion'}
    elif role == ROLES['SCHOOL_APPROVER']:
        editable = {'review_stage', 'school_review_result', 'provincial_award_level', 'national_award_level', 'research_admin_opinion'}
    elif role == ROLES['JUDGE']:
        editable = {'review_stage', 'college_review_result', 'school_review_result', 'research_admin_opinion', 'department_head_opinion'}

    updates = {}

    if 'review_stage' in editable and 'review_stage' in data:
        v = normalize_review_stage(data.get('review_stage'))
        if v and v not in ['school', 'provincial', 'national']:
            return fail('当前竞赛阶段无效', 400)
        updates['review_stage'] = v

    if 'college_review_result' in editable and 'college_review_result' in data:
        v = normalize_review_result(data.get('college_review_result'))
        if v and v not in ['approved', 'rejected', 'pending']:
            return fail('学院赛评审结果无效', 400)
        updates['college_review_result'] = v

    if 'school_review_result' in editable and 'school_review_result' in data:
        v = normalize_review_result(data.get('school_review_result'))
        if v and v not in ['approved', 'rejected', 'pending']:
            return fail('校赛评审结果无效', 400)
        updates['school_review_result'] = v

    if 'provincial_award_level' in editable and 'provincial_award_level' in data:
        v = normalize_award_level(data.get('provincial_award_level'))
        if v and v not in ['special', 'first', 'second', 'third', 'excellent', 'none']:
            return fail('省赛获奖等级无效', 400)
        updates['provincial_award_level'] = v

    if 'national_award_level' in editable and 'national_award_level' in data:
        v = normalize_award_level(data.get('national_award_level'))
        if v and v not in ['gold', 'silver', 'bronze', 'special', 'first', 'second', 'third', 'excellent', 'none']:
            return fail('国赛获奖等级无效', 400)
        updates['national_award_level'] = v

    if 'research_admin_opinion' in editable and 'research_admin_opinion' in data:
        updates['research_admin_opinion'] = (data.get('research_admin_opinion') or '').strip()

    if 'department_head_opinion' in editable and 'department_head_opinion' in data:
        updates['department_head_opinion'] = (data.get('department_head_opinion') or '').strip()

    if not updates:
        return success(message='无可更新字段')

    try:
        sets = ', '.join([f"{k} = ?" for k in updates.keys()])
        params = list(updates.values()) + [project_id]
        conn.execute(f'UPDATE projects SET {sets} WHERE id = ?', params)
        log_action(conn, user_id, 'ADMIN_REVIEW_UPDATE', f'Project {project_id} {",".join(updates.keys())}', request.remote_addr)
        conn.commit()
        return success(message='保存成功')
    except Exception as e:
        conn.rollback()
        return fail(str(e), 500)


@projects_bp.route('/projects/<int:project_id>/competition-results', methods=['PUT'])
@login_required
@role_required([ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN'], ROLES['SCHOOL_APPROVER']])
def update_competition_results(project_id):
    if project_id in GHOST_PROJECT_IDS:
        return fail('项目不存在', 404)

    user_id = session.get('user_id')
    role = session.get('role')
    data = request.json or {}

    conn = get_db_connection()
    project = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    if not project:
        return fail('项目不存在', 404)
    if not can_view_project(conn, role, user_id, dict(project)):
        return fail('无权限', 403)

    row_for_tpl = dict(project)
    comp_id = project['competition_id'] if 'competition_id' in project.keys() else None
    if comp_id:
        comp = conn.execute('SELECT template_type, title FROM competitions WHERE id = ?', (comp_id,)).fetchone()
        if comp:
            row_for_tpl['competition_template_type'] = comp['template_type']
            row_for_tpl['competition_title'] = comp['title']
    template_name = resolve_template_name(row_for_tpl)
    if template_name != '大挑':
        return fail('仅支持大挑项目录入', 400)

    prov_status = (data.get('provincial_status') or '').strip()
    nat_status = (data.get('national_status') or '').strip()
    allowed_status = {'未参赛', '已参赛', '已获奖'}
    if prov_status and prov_status not in allowed_status:
        return fail('省赛状态无效', 400)
    if nat_status and nat_status not in allowed_status:
        return fail('国赛状态无效', 400)

    prov_award = normalize_award_level(data.get('provincial_award_level'))
    if prov_award and prov_award not in ['special', 'first', 'second', 'third', 'excellent', 'none']:
        return fail('省赛获奖等级无效', 400)

    nat_award = normalize_award_level(data.get('national_award_level'))
    if nat_award and nat_award not in ['gold', 'silver', 'bronze', 'none']:
        return fail('国赛获奖等级无效', 400)

    prov_cert = (data.get('provincial_certificate_no') or '').strip()
    nat_cert = (data.get('national_certificate_no') or '').strip()
    prov_comment = (data.get('provincial_review_comment') or '').strip()
    nat_comment = (data.get('national_review_comment') or '').strip()
    advance_national = 1 if data.get('provincial_advance_national') else 0

    if prov_award and prov_award != 'none':
        prov_status = '已获奖'
    if advance_national and not nat_status:
        nat_status = '未参赛'
    if nat_award and nat_award != 'none':
        nat_status = '已获奖'

    try:
        conn.execute(
            '''
            UPDATE projects
            SET provincial_status = ?,
                provincial_award_level = ?,
                provincial_certificate_no = ?,
                provincial_advance_national = ?,
                provincial_review_comment = ?,
                national_status = ?,
                national_award_level = ?,
                national_certificate_no = ?,
                national_review_comment = ?
            WHERE id = ?
            ''',
            (
                prov_status,
                prov_award or (project['provincial_award_level'] or 'none'),
                prov_cert,
                advance_national,
                prov_comment,
                nat_status,
                nat_award or (project['national_award_level'] or 'none'),
                nat_cert,
                nat_comment,
                project_id,
            ),
        )

        if advance_national:
            conn.execute('UPDATE projects SET current_level = ?, review_stage = ? WHERE id = ?', ('national', 'national', project_id))
            conn.execute(
                'INSERT OR REPLACE INTO project_node_status (project_id, node_name, current_status, comment, award_level, updated_by, updated_at) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)',
                (project_id, '省赛', '已晋级', '', '', user_id)
            )
            conn.execute(
                'INSERT OR IGNORE INTO project_node_status (project_id, node_name, current_status, comment, award_level, updated_by, updated_at) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)',
                (project_id, '国赛', '待评审', '', '', user_id)
            )
        elif prov_status in ['已参赛', '已获奖']:
            conn.execute(
                'INSERT OR REPLACE INTO project_node_status (project_id, node_name, current_status, comment, award_level, updated_by, updated_at) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)',
                (project_id, '省赛', '未晋级', '', '', user_id)
            )

        if nat_status == '已获奖' and nat_award and nat_award != 'none':
            conn.execute(
                'UPDATE projects SET level = ? WHERE id = ?',
                ('国赛获奖', project_id)
            )
            conn.execute(
                'INSERT OR REPLACE INTO project_node_status (project_id, node_name, current_status, comment, award_level, updated_by, updated_at) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)',
                (project_id, '国赛', '已获奖', nat_comment, nat_award, user_id)
            )
        elif nat_status == '已参赛':
            conn.execute(
                'INSERT OR IGNORE INTO project_node_status (project_id, node_name, current_status, comment, award_level, updated_by, updated_at) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)',
                (project_id, '国赛', '待评审', '', '', user_id)
            )

        create_notification(
            conn,
            project['created_by'],
            '省赛/国赛结果更新',
            f'项目《{project["title"]}》省赛/国赛结果已更新。',
            'project'
        )
        log_action(conn, user_id, 'COMPETITION_RESULTS_UPDATE', f'Project {project_id} provincial/national results', request.remote_addr)
        conn.commit()
        return success(message='保存成功')
    except Exception as e:
        conn.rollback()
        return fail(str(e), 500)


@projects_bp.route('/projects/<int:project_id>/awards', methods=['GET'])
@login_required
def get_project_awards(project_id):
    if project_id in GHOST_PROJECT_IDS:
        return fail('项目不存在', 404)

    user_id = session.get('user_id')
    role = session.get('role')
    conn = get_db_connection()
    project = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    if not project:
        return fail('项目不存在', 404)
    if not can_view_project(conn, role, user_id, dict(project)):
        return fail('无权限', 403)

    rows = conn.execute(
        'SELECT * FROM project_awards WHERE project_id = ? ORDER BY created_at DESC',
        (project_id,)
    ).fetchall()
    return success(data=[dict(r) for r in rows])


@projects_bp.route('/projects/<int:project_id>/awards', methods=['POST'])
@login_required
@role_required([ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN'], ROLES['SCHOOL_APPROVER']])
def create_project_award(project_id):
    if project_id in GHOST_PROJECT_IDS:
        return fail('项目不存在', 404)

    user_id = session.get('user_id')
    data = request.json or {}
    stage = normalize_review_stage(data.get('stage'))
    award_level = normalize_award_level(data.get('award_level'))

    if stage not in ['provincial', 'national']:
        return fail('赛事阶段无效', 400)
    if award_level not in ['special', 'first', 'second', 'third', 'excellent', 'none']:
        return fail('获奖等级无效', 400)

    conn = get_db_connection()
    project = conn.execute('SELECT id, title, created_by FROM projects WHERE id = ?', (project_id,)).fetchone()
    if not project:
        return fail('项目不存在', 404)

    try:
        conn.execute(
            '''
            INSERT INTO project_awards (project_id, stage, award_level, award_name, award_time, issuer, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                project_id,
                stage,
                award_level,
                (data.get('award_name') or '').strip(),
                (data.get('award_time') or '').strip(),
                (data.get('issuer') or '').strip(),
                user_id
            )
        )
        create_notification(conn, project['created_by'], '获奖记录更新', f'项目《{project["title"]}》新增获奖记录（{stage}）', 'system')
        log_action(conn, user_id, 'AWARD_CREATE', f'Project {project_id} stage={stage} level={award_level}', request.remote_addr)
        conn.commit()
        return success(message='已新增获奖记录')
    except Exception as e:
        conn.rollback()
        return fail(str(e), 500)


@projects_bp.route('/awards', methods=['GET'])
@login_required
@role_required([ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN'], ROLES['SCHOOL_APPROVER']])
def list_awards():
    conn = get_db_connection()
    rows = conn.execute(
        '''
        SELECT a.*, p.title AS project_title
        FROM project_awards a
        JOIN projects p ON a.project_id = p.id
        ORDER BY a.created_at DESC
        '''
    ).fetchall()
    return success(data=[dict(r) for r in rows])


@projects_bp.route('/awards/<int:award_id>', methods=['PUT'])
@login_required
@role_required([ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN'], ROLES['SCHOOL_APPROVER']])
def update_award(award_id):
    user_id = session.get('user_id')
    data = request.json or {}
    stage = normalize_review_stage(data.get('stage'))
    award_level = normalize_award_level(data.get('award_level'))

    if stage not in ['provincial', 'national']:
        return fail('赛事阶段无效', 400)
    if award_level not in ['special', 'first', 'second', 'third', 'excellent', 'none']:
        return fail('获奖等级无效', 400)

    conn = get_db_connection()
    row = conn.execute('SELECT * FROM project_awards WHERE id = ?', (award_id,)).fetchone()
    if not row:
        return fail('获奖记录不存在', 404)

    try:
        conn.execute(
            '''
            UPDATE project_awards
            SET stage = ?, award_level = ?, award_name = ?, award_time = ?, issuer = ?
            WHERE id = ?
            ''',
            (
                stage,
                award_level,
                (data.get('award_name') or '').strip(),
                (data.get('award_time') or '').strip(),
                (data.get('issuer') or '').strip(),
                award_id
            )
        )
        log_action(conn, user_id, 'AWARD_UPDATE', f'Award {award_id}', request.remote_addr)
        conn.commit()
        return success(message='已更新获奖记录')
    except Exception as e:
        conn.rollback()
        return fail(str(e), 500)


@projects_bp.route('/awards/<int:award_id>', methods=['DELETE'])
@login_required
@role_required([ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN'], ROLES['SCHOOL_APPROVER']])
def delete_award(award_id):
    user_id = session.get('user_id')
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM project_awards WHERE id = ?', (award_id,)).fetchone()
    if not row:
        return fail('获奖记录不存在', 404)

    try:
        conn.execute('DELETE FROM project_awards WHERE id = ?', (award_id,))
        log_action(conn, user_id, 'AWARD_DELETE', f'Award {award_id}', request.remote_addr)
        conn.commit()
        return success(message='已删除获奖记录')
    except Exception as e:
        conn.rollback()
        return fail(str(e), 500)
