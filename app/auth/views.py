from flask import Blueprint, request, session, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from app.utils.db import get_db_connection
from app.utils.response import success, fail
from app.utils.auth import login_required, issue_auth_token, revoke_auth_token, set_token_active_role, get_auth_context
from config import get_config
from flasgger import swag_from
import sqlite3
import json

config = get_config()
ROLES = config.ROLES

auth_bp = Blueprint('auth', __name__, url_prefix='/api')

# Helper for logging actions (moved from app.py)
def log_action(conn, user_id, action, details, ip_address):
    try:
        conn.execute('INSERT INTO system_logs (user_id, action, details, ip_address) VALUES (?, ?, ?, ?)',
                    (user_id, action, details, ip_address))
    except Exception as e:
        print(f"LOG ERROR: {e}")

@auth_bp.route('/login', methods=['POST'])
@swag_from({
    'tags': ['认证模块'],
    'summary': '用户登录',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'username': {'type': 'string', 'example': 'admin'},
                    'password': {'type': 'string', 'example': 'admin123'}
                }
            }
        }
    ],
    'responses': {
        200: {'description': '登录成功'},
        401: {'description': '用户名或密码错误'},
        403: {'description': '账号待审核或已禁用'}
    }
})
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    
    if user and check_password_hash(user['password'], password):
        ud = dict(user)
        if ud.get('status') == 'pending':
            return fail('账号待审核中，请耐心等待', 403)
        elif ud.get('status') == 'disabled':
            return fail('账号已被禁用', 403)
            
        # 处理多角色
        roles = []
        try:
            roles = json.loads(ud.get('roles') or '[]')
        except:
            pass
            
        if not roles:
            roles = [ud['role']]

        mode = (data.get('session_mode') or request.headers.get('X-Session-Mode') or '').strip().lower()
        token_mode = mode == 'token'
        active_role = roles[0]

        if token_mode:
            token = issue_auth_token(ud['id'], active_role, roles, ud.get('college', ''))
            ud['auth_token'] = token
            ud['active_role'] = active_role
            ud['all_roles'] = roles
            log_action(conn, ud['id'], 'LOGIN', f"User logged in (token) as {active_role}", request.remote_addr)
        else:
            session['user_id'] = ud['id']
            session['role'] = active_role
            session['roles'] = roles
            session['college'] = ud.get('college', '')
            ud['active_role'] = session['role']
            ud['all_roles'] = session['roles']
            log_action(conn, ud['id'], 'LOGIN', f"User logged in as {session['role']}", request.remote_addr)

        conn.commit()
        
        if 'password' in ud: del ud['password']
        return success(data=ud, message='登录成功')
    
    return fail('用户名或密码错误', 401)


@auth_bp.route('/auth/forgot_password', methods=['POST'])
def forgot_password():
    data = request.json or {}
    username = (data.get('username') or '').strip()
    if not username:
        return fail('请输入工号/学号', 400)

    conn = get_db_connection()
    try:
        user_row = conn.execute('SELECT id, status, real_name, college, role FROM users WHERE username = ?', (username,)).fetchone()
        if not user_row:
            return fail('账号不存在', 404)
        user = dict(user_row)
        if (user.get('status') or '') == 'disabled':
            return fail('账号已禁用', 403)

        conn.execute('UPDATE users SET password = ? WHERE id = ?', (generate_password_hash('123456'), user['id']))

        title = '密码重置提醒'
        content = f'账号「{username}」已通过“忘记密码”重置为默认密码，请提醒用户尽快修改。'
        admin_roles = [ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN'], ROLES['SCHOOL_APPROVER']]
        rows = conn.execute(
            f"SELECT id FROM users WHERE status != 'disabled' AND role IN ({','.join(['?'] * len(admin_roles))})",
            admin_roles
        ).fetchall()
        for r in rows:
            conn.execute(
                'INSERT INTO notifications (user_id, title, content, type) VALUES (?, ?, ?, ?)',
                (r['id'], title, content, 'security')
            )
        try:
            log_action(conn, user['id'], 'FORGOT_PASSWORD', f"Reset password for {username}", request.remote_addr)
        except Exception:
            pass

        conn.commit()
        return success(message='已重置为 123456')
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return fail(str(e), 500)

@auth_bp.route('/register', methods=['POST'])
@swag_from({
    'tags': ['认证模块'],
    'summary': '用户注册',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'username': {'type': 'string'},
                    'password': {'type': 'string'},
                    'role': {'type': 'string', 'enum': ['student', 'teacher']},
                    'real_name': {'type': 'string'},
                    'identity_number': {'type': 'string'},
                    'college': {'type': 'string'}
                }
            }
        }
    ],
    'responses': {
        200: {'description': '注册成功，等待审核'},
        400: {'description': '信息不完整或用户名已存在'}
    }
})
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    role = data.get('role') # teacher, student
    
    if not username or not password or not role:
        return fail('信息不完整', 400)
        
    if role not in [ROLES['TEACHER'], ROLES['STUDENT']]:
        return fail('只能注册学生或导师账号', 400)
        
    conn = get_db_connection()
    try:
        hashed_password = generate_password_hash(password)
        conn.execute('BEGIN TRANSACTION')
        conn.execute('''
            INSERT INTO users (username, password, role, real_name, identity_number, department, college, personal_info, teaching_office, research_area, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        ''', (
            username, 
            hashed_password, 
            role,
            data.get('real_name'),
            data.get('identity_number'),
            data.get('department'),
            data.get('college'),
            data.get('personal_info', ''),
            data.get('teaching_office', ''),
            data.get('research_area', '')
        ))
        new_user_id = conn.execute('SELECT last_insert_rowid() as id').fetchone()['id']

        reg_college = (data.get('college') or '').strip()
        short_college = reg_college.split('（')[0].split('(')[0].strip() if reg_college else ''
        recipients = []

        base_admin_roles = [ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN'], ROLES['SCHOOL_APPROVER']]
        rows = conn.execute(
            f'''
            SELECT id FROM users
            WHERE status != 'disabled'
              AND role IN ({",".join(["?"] * len(base_admin_roles))})
            ''',
            base_admin_roles
        ).fetchall()
        recipients.extend([r['id'] for r in rows])

        if reg_college:
            rows = conn.execute(
                '''
                SELECT id FROM users
                WHERE status != 'disabled'
                  AND role = ?
                  AND (
                        college = ?
                        OR college LIKE ?
                        OR college LIKE ?
                      )
                ''',
                (
                    ROLES['COLLEGE_APPROVER'],
                    reg_college,
                    f"{short_college}%",
                    f"%{short_college}%",
                )
            ).fetchall()
            recipients.extend([r['id'] for r in rows])

        recipients = sorted(set([int(x) for x in recipients if x]))
        title = '新增用户注册待审核'
        content = f'用户「{username}」已提交注册申请，请前往“用户管理-待审核用户”处理。'
        for rid in recipients:
            conn.execute(
                'INSERT INTO notifications (user_id, title, content, type) VALUES (?, ?, ?, ?)',
                (rid, title, content, 'user')
            )

        try:
            log_action(conn, new_user_id, 'REGISTER', f"User registered (pending). Notify {len(recipients)} admins.", request.remote_addr)
        except Exception:
            pass

        conn.execute('COMMIT')
        return success(message='注册申请已提交，等待管理员审核')
    except sqlite3.IntegrityError:
        try:
            conn.execute('ROLLBACK')
        except Exception:
            pass
        return fail('用户名已存在', 400)
    except Exception as e:
        try:
            conn.execute('ROLLBACK')
        except Exception:
            pass
        return fail(str(e), 500)

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    ctx = get_auth_context() or {}
    user_id = ctx.get('user_id') or session.get('user_id')
    token = ctx.get('token') if ctx.get('mode') == 'token' else ''
    if user_id:
        conn = get_db_connection()
        log_action(conn, user_id, 'LOGOUT', 'User logged out', request.remote_addr)
        conn.commit()
    if token:
        revoke_auth_token(token)
        return success(message='已登出')
    session.clear()
    return success(message='已登出')

@auth_bp.route('/me', methods=['GET'])
@login_required
@swag_from({
    'tags': ['认证模块'],
    'summary': '获取当前登录用户信息',
    'responses': {
        200: {'description': '获取成功'},
        401: {'description': '未登录'},
        404: {'description': '用户不存在'}
    }
})
def get_me():
    user_id = session.get('user_id')
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if user:
        ud = dict(user)
        if 'password' in ud: del ud['password']
        
        # 处理多角色
        roles = []
        try:
            roles = json.loads(ud.get('roles') or '[]')
        except:
            pass
        if not roles:
            roles = [ud['role']]
            
        ud['active_role'] = session.get('role', ud['role'])
        ud['all_roles'] = roles
        
        return success(data=ud)
    return fail('用户不存在', 404)

@auth_bp.route('/me', methods=['PUT'])
@login_required
def update_my_profile():
    user_id = session.get('user_id')
    data = request.json
    allowed_fields = ['real_name', 'college', 'department', 'personal_info', 'email', 'phone', 'identity_number', 'teaching_office', 'research_area']
    
    conn = get_db_connection()
    try:
        fields = []
        values = []
        for field in allowed_fields:
            if field in data:
                fields.append(f"{field} = ?")
                values.append(data[field])
                
        if not fields:
            return success(message='无变更')
            
        values.append(user_id)
        conn.execute(f'UPDATE users SET {", ".join(fields)} WHERE id = ?', values)
        conn.commit()
        return success(message='个人信息更新成功')
    except Exception as e:
        return fail(str(e), 500)

@auth_bp.route('/switch_role', methods=['POST'])
@auth_bp.route('/auth/switch_role', methods=['POST'])
@login_required
def switch_role():
    data = request.json
    new_role = data.get('role')
    allowed_roles = session.get('roles', [])
    
    if new_role not in allowed_roles:
        return fail('您无权切换至该角色', 403)
        
    ctx = get_auth_context() or {}
    if ctx.get('mode') == 'token' and ctx.get('token'):
        set_token_active_role(ctx['token'], new_role)
        session['role'] = new_role
        session.modified = False
    else:
        session['role'] = new_role
    
    conn = get_db_connection()
    log_action(conn, session.get('user_id'), 'SWITCH_ROLE', f"User switched active role to {new_role}", request.remote_addr)
    conn.commit()
    
    return success(data={'active_role': new_role}, message='角色切换成功')

@auth_bp.route('/auth/fork_token', methods=['POST'])
@login_required
def fork_token():
    ctx = get_auth_context() or {}
    if ctx.get('mode') != 'token' or not ctx.get('token'):
        return fail('仅支持 Token 会话', 400)
    token = issue_auth_token(ctx['user_id'], ctx.get('role'), ctx.get('roles', []), ctx.get('college', ''))
    return success(data={'auth_token': token}, message='已分离会话')

@auth_bp.route('/auth/issue_token', methods=['POST'])
@login_required
def issue_token_from_cookie():
    ctx = get_auth_context() or {}
    if ctx.get('mode') == 'token' and ctx.get('token'):
        return success(data={'auth_token': ctx['token']})
    roles = session.get('roles', []) or []
    if not roles:
        r = session.get('role')
        roles = [r] if r else []
    token = issue_auth_token(session.get('user_id'), session.get('role') or (roles[0] if roles else ''), roles, session.get('college', ''))
    return success(data={'auth_token': token})

@auth_bp.route('/me/password', methods=['PUT'])
@login_required
def change_my_password():
    user_id = session.get('user_id')
    data = request.json
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    if not old_password or not new_password:
        return fail('请提供新旧密码', 400)
        
    conn = get_db_connection()
    user = conn.execute('SELECT password FROM users WHERE id = ?', (user_id,)).fetchone()
    
    if user and check_password_hash(user['password'], old_password):
        hashed_new_password = generate_password_hash(new_password)
        conn.execute('UPDATE users SET password = ? WHERE id = ?', (hashed_new_password, user_id))
        conn.commit()
        ctx = get_auth_context() or {}
        if ctx.get('mode') == 'token' and ctx.get('token'):
            revoke_auth_token(ctx['token'])
            return success(message='密码修改成功，请重新登录')
        session.clear()
        return success(message='密码修改成功，请重新登录')
    else:
        return fail('旧密码不正确', 400)
