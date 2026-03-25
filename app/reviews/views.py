from flask import Blueprint, request, session
from app.utils.db import get_db_connection
from app.utils.response import success, fail
from app.utils.auth import login_required, role_required
from config import get_config
import json

config = get_config()
ROLES = config.ROLES

reviews_bp = Blueprint('reviews', __name__, url_prefix='/api/reviews')

@reviews_bp.route('/tasks', methods=['GET'])
@login_required
def get_my_tasks():
    user_id = session.get('user_id')
    conn = get_db_connection()
    tasks = conn.execute('''
        SELECT t.*, p.title as project_title, p.project_type, p.competition_id
        FROM review_tasks t
        JOIN projects p ON t.project_id = p.id
        WHERE t.judge_id = ?
        ORDER BY t.created_at DESC
    ''', (user_id,)).fetchall()
    
    result = []
    for t in tasks:
        task_dict = dict(t)
        # Fetch scores if any
        scores = conn.execute('SELECT * FROM review_scores WHERE task_id = ?', (t['id'],)).fetchall()
        task_dict['criteria_scores'] = {s['criteria']: s['score'] for s in scores}
        result.append(task_dict)
        
    return success(data=result)

@reviews_bp.route('/tasks/<int:task_id>', methods=['POST'])
@login_required
def submit_task(task_id):
    user_id = session.get('user_id')
    data = request.json
    status = data.get('status', 'draft') # 'draft' or 'completed'
    comments = data.get('comments', '')
    criteria_scores = data.get('criteria_scores', {})
    
    conn = get_db_connection()
    task = conn.execute('SELECT * FROM review_tasks WHERE id = ? AND judge_id = ?', (task_id, user_id)).fetchone()
    if not task:
        return fail('任务不存在或无权限', 404)
        
    if task['status'] == 'completed':
        return fail('任务已提交，不可修改', 400)
        
    total_score = sum(int(v) for v in criteria_scores.values())
    
    try:
        conn.execute('BEGIN TRANSACTION')
        conn.execute('UPDATE review_tasks SET status = ?, score = ?, comments = ? WHERE id = ?',
                     (status, total_score, comments, task_id))
                     
        conn.execute('DELETE FROM review_scores WHERE task_id = ?', (task_id,))
        for criteria, score in criteria_scores.items():
            max_score = 30 if criteria in ['scientific', 'advanced'] else 20
            conn.execute('INSERT INTO review_scores (task_id, criteria, score, max_score) VALUES (?, ?, ?, ?)',
                         (task_id, criteria, int(score), max_score))
                         
        conn.execute('COMMIT')
        return success(message='保存成功')
    except Exception as e:
        conn.execute('ROLLBACK')
        return fail(str(e), 500)

@reviews_bp.route('/assign', methods=['POST'])
@login_required
@role_required([ROLES['COLLEGE_APPROVER'], ROLES['SCHOOL_APPROVER'], ROLES['PROJECT_ADMIN'], ROLES['SYSTEM_ADMIN']])
def assign_reviewers():
    data = request.json
    project_id = data.get('project_id')
    judge_ids = data.get('judge_ids', [])
    review_level = data.get('review_level', 'college')
    
    if not project_id or not judge_ids:
        return fail('参数不完整', 400)
        
    conn = get_db_connection()
    try:
        conn.execute('BEGIN TRANSACTION')
        for j_id in judge_ids:
            # Check if already assigned
            existing = conn.execute('SELECT id FROM review_tasks WHERE project_id = ? AND judge_id = ? AND review_level = ?',
                                    (project_id, j_id, review_level)).fetchone()
            if not existing:
                conn.execute('INSERT INTO review_tasks (project_id, judge_id, review_level, status) VALUES (?, ?, ?, ?)',
                             (project_id, j_id, review_level, 'pending'))
        conn.execute('COMMIT')
        return success(message='分配成功')
    except Exception as e:
        conn.execute('ROLLBACK')
        return fail(str(e), 500)

@reviews_bp.route('/calc_rank', methods=['POST'])
@login_required
@role_required([ROLES['COLLEGE_APPROVER'], ROLES['SCHOOL_APPROVER'], ROLES['PROJECT_ADMIN'], ROLES['SYSTEM_ADMIN']])
def calc_rank():
    data = request.json
    review_level = data.get('review_level', 'college')
    
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
        for row in avg_scores:
            conn.execute(f'UPDATE projects SET {score_field} = ? WHERE id = ?', (row['avg_score'], row['project_id']))
            
        # 2. Calculate ranks partitioned by competition_id
        competitions = conn.execute('SELECT DISTINCT competition_id FROM projects WHERE competition_id IS NOT NULL').fetchall()
        for comp in competitions:
            c_id = comp['competition_id']
            projects = conn.execute(f'''
                SELECT id, {score_field} as score 
                FROM projects 
                WHERE competition_id = ? AND {score_field} IS NOT NULL
                ORDER BY {score_field} DESC
            ''', (c_id,)).fetchall()
            
            rank_field = f'{review_level}_rank'
            rank = 1
            for p in projects:
                conn.execute(f'UPDATE projects SET {rank_field} = ? WHERE id = ?', (rank, p['id']))
                rank += 1
            
        conn.execute('COMMIT')
        return success(message='计算完成')
    except Exception as e:
        conn.execute('ROLLBACK')
        return fail(str(e), 500)

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
                conn.execute(
                    'INSERT INTO notifications (user_id, title, content, type) VALUES (?, ?, ?, ?)',
                    (m['user_id'], '新增校赛评审任务', f'项目《{p["title"]}》已进入校赛，请在“我的评审任务”中完成评审。', 'project')
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
    data = request.json or {}
    project_id = data.get('project_id', 1)
    review_level = data.get('review_level', 'college')

    conn = get_db_connection()

    project = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    if not project:
        return fail('项目不存在', 404)

    team = None
    if review_level == 'college':
        team = conn.execute(
            'SELECT * FROM review_teams WHERE level = ? AND college = ? AND enabled = 1 ORDER BY id LIMIT 1',
            ('college', project['college'])
        ).fetchone()
        if not team:
            team = conn.execute(
                'SELECT * FROM review_teams WHERE level = ? AND college = ? AND enabled = 1 ORDER BY id LIMIT 1',
                ('college', '计算机学院')
            ).fetchone()
    else:
        team = conn.execute(
            'SELECT * FROM review_teams WHERE level = ? AND discipline_group = ? AND enabled = 1 ORDER BY id LIMIT 1',
            ('school', data.get('discipline_group', '理工组'))
        ).fetchone()

    if not team:
        return fail('未找到可用评审团队', 400)

    members = conn.execute(
        'SELECT user_id FROM review_team_members WHERE team_id = ?',
        (team['id'],)
    ).fetchall()
    if not members:
        return fail('评审团队没有成员', 400)

    created = 0
    for m in members:
        exists = conn.execute(
            'SELECT id FROM review_tasks WHERE project_id = ? AND judge_id = ? AND review_level = ?',
            (project_id, m['user_id'], review_level)
        ).fetchone()
        if exists:
            continue
        conn.execute(
            'INSERT INTO review_tasks (project_id, judge_id, review_level, team_id, status, score, comments) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (project_id, m['user_id'], review_level, team['id'], 'pending', 0, '')
        )
        created += 1

    if project['status'] == 'pending':
        conn.execute('UPDATE projects SET status = ? WHERE id = ?', ('under_review', project_id))

    conn.commit()
    return success(data={'created_tasks': created, 'team_id': team['id']}, message='初始化成功')
