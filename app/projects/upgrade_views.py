from flask import request, session
from app.utils.db import get_db_connection
from app.utils.response import success, fail
from app.utils.auth import login_required, role_required
from config import get_config

config = get_config()
ROLES = config.ROLES

def create_notification(conn, user_id, title, content, n_type='system'):
    conn.execute('INSERT INTO notifications (user_id, title, content, type) VALUES (?, ?, ?, ?)',
                (user_id, title, content, n_type))

def request_project_upgrade():
    """学生提交项目升级申请"""
    user_id = session.get('user_id')
    data = request.json
    project_id = data.get('project_id')
    target_level = data.get('target_level') # '省级' 或 '国家级'
    reason = data.get('reason', '')

    if not project_id or not target_level:
        return fail('参数不完整', 400)
    
    if target_level not in ['省级', '国家级']:
        return fail('目标级别无效', 400)

    conn = get_db_connection()
    project = conn.execute('SELECT * FROM projects WHERE id = ? AND created_by = ?', (project_id, user_id)).fetchone()
    if not project:
        return fail('项目不存在或无权操作', 403)
    
    current_level = project['level'] or '校级'
    
    # 校验升级逻辑
    # 允许校级申请升级为省级或国家级
    if current_level == '校级' and target_level not in ['省级', '国家级']:
        return fail('目标级别无效', 400)
    if current_level == '省级' and target_level != '国家级':
        return fail('省级项目仅能申请升级为国家级', 400)
    if current_level == '国家级':
        return fail('国家级项目已是最高级别', 400)

    # 检查是否有正在处理的申请
    existing = conn.execute('SELECT id FROM project_upgrades WHERE project_id = ? AND status NOT IN ("approved", "rejected")', (project_id,)).fetchone()
    if existing:
        return fail('该项目已有正在处理中的升级申请', 400)

    try:
        conn.execute('''
            INSERT INTO project_upgrades (project_id, applicant_id, current_level, target_level, reason, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (project_id, user_id, current_level, target_level, reason, 'pending_college'))
        conn.commit()
        return success(message='申请已提交，等待学院审核')
    except Exception as e:
        conn.rollback()
        return fail(str(e), 500)

def get_pending_upgrades():
    """获取待审核的升级申请"""
    user_id = session.get('user_id')
    role = session.get('role')
    conn = get_db_connection()
    
    user_info = conn.execute('SELECT college FROM users WHERE id = ?', (user_id,)).fetchone()
    college = user_info['college'] if user_info else None

    query = '''
        SELECT u.*, p.title as project_title, p.college as project_college, p.leader_name, usr.real_name as applicant_name
        FROM project_upgrades u
        JOIN projects p ON u.project_id = p.id
        JOIN users usr ON u.applicant_id = usr.id
        WHERE 1=1
    '''
    params = []

    if role == ROLES['COLLEGE_APPROVER']:
        query += " AND u.status = 'pending_college' AND p.college = ?"
        params.append(college)
    elif role == ROLES['SCHOOL_APPROVER']:
        query += " AND u.status = 'pending_school'"
    elif role in [ROLES['PROJECT_ADMIN'], ROLES['SYSTEM_ADMIN']]:
        # 管理员可以看到所有阶段
        pass
    else:
        return fail('无权查看审核列表', 403)

    upgrades = conn.execute(query, params).fetchall()
    return success(data=[dict(u) for u in upgrades])

def audit_project_upgrade(upgrade_id):
    """审核项目升级申请"""
    user_id = session.get('user_id')
    role = session.get('role')
    data = request.json
    action = data.get('action') # 'approve' or 'reject'
    opinion = data.get('opinion', '')

    if action not in ['approve', 'reject']:
        return fail('操作无效', 400)

    conn = get_db_connection()
    upgrade = conn.execute('SELECT * FROM project_upgrades WHERE id = ?', (upgrade_id,)).fetchone()
    if not upgrade:
        return fail('申请记录不存在', 404)
    
    project = conn.execute('SELECT * FROM projects WHERE id = ?', (upgrade['project_id'],)).fetchone()
    
    current_status = upgrade['status']
    next_status = ''
    
    # 流程控制
    if current_status == 'pending_college':
        if role != ROLES['COLLEGE_APPROVER']:
            return fail('仅学院管理员可进行此环节审核', 403)
        # 学院仅能审本院
        user_row = conn.execute('SELECT college FROM users WHERE id = ?', (user_id,)).fetchone()
        user_college = user_row['college'] if user_row else None
        if project['college'] != user_college:
            return fail('无权审核其他学院的项目', 403)
        next_status = 'pending_school' if action == 'approve' else 'rejected'
        update_sql = "UPDATE project_upgrades SET status = ?, college_opinion = ?, college_reviewer_id = ?, college_reviewed_at = CURRENT_TIMESTAMP WHERE id = ?"
        params = (next_status, opinion, user_id, upgrade_id)
        
    elif current_status == 'pending_school':
        if role != ROLES['SCHOOL_APPROVER']:
            return fail('仅学校管理员可进行此环节审核', 403)
        
        next_status = 'approved' if action == 'approve' else 'rejected'
            
        update_sql = "UPDATE project_upgrades SET status = ?, school_opinion = ?, school_reviewer_id = ?, school_reviewed_at = CURRENT_TIMESTAMP WHERE id = ?"
        params = (next_status, opinion, user_id, upgrade_id)

    else:
        return fail('当前申请状态不可审核', 400)

    try:
        conn.execute('BEGIN TRANSACTION')
        conn.execute(update_sql, params)
        
        # 如果最终通过，更新项目级别
        if next_status == 'approved':
            # 更新项目表
            conn.execute('UPDATE projects SET level = ? WHERE id = ?', (upgrade['target_level'], upgrade['project_id']))
            # 同步更新通知
            create_notification(conn, upgrade['applicant_id'], '项目升级成功', f'您的项目《{project["title"]}》已成功升级为{upgrade["target_level"]}。', 'approval')
        elif next_status == 'rejected':
            create_notification(conn, upgrade['applicant_id'], '项目升级被驳回', f'您的项目《{project["title"]}》升级申请已被驳回。意见：{opinion}', 'approval')
        else:
            create_notification(conn, upgrade['applicant_id'], '项目升级进度更新', f'您的项目《{project["title"]}》升级申请已通过当前环节，进入下一阶段。', 'info')

        conn.commit()
        return success(message='审核操作成功')
    except Exception as e:
        conn.rollback()
        return fail(str(e), 500)

def get_upgrade_history(project_id):
    """获取项目的升级申请历史（含审批留痕）"""
    conn = get_db_connection()
    history = conn.execute('''
        SELECT u.*, 
               u1.real_name as college_reviewer, 
               u2.real_name as school_reviewer,
               u3.real_name as provincial_reviewer,
               u4.real_name as national_reviewer
        FROM project_upgrades u
        LEFT JOIN users u1 ON u.college_reviewer_id = u1.id
        LEFT JOIN users u2 ON u.school_reviewer_id = u2.id
        LEFT JOIN users u3 ON u.provincial_reviewer_id = u3.id
        LEFT JOIN users u4 ON u.national_reviewer_id = u4.id
        WHERE u.project_id = ?
        ORDER BY u.created_at DESC
    ''', (project_id,)).fetchall()
    return success(data=[dict(h) for h in history])
