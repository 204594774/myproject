from flask import Blueprint, request, session, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from app.utils.db import get_db_connection
from app.utils.response import success, fail
from app.utils.auth import login_required
from config import get_config
from flasgger import swag_from
import sqlite3

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
            
        session['user_id'] = ud['id']
        session['role'] = ud['role']
        session['college'] = ud.get('college', '')
        
        log_action(conn, ud['id'], 'LOGIN', 'User logged in', request.remote_addr)
        conn.commit()
        
        # 不要返回密码
        if 'password' in ud: del ud['password']
        return success(data=ud, message='登录成功')
    
    return fail('用户名或密码错误', 401)

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
        conn.commit()
        return success(message='注册申请已提交，等待管理员审核')
    except sqlite3.IntegrityError:
        return fail('用户名已存在', 400)
    except Exception as e:
        return fail(str(e), 500)

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    user_id = session.get('user_id')
    if user_id:
        conn = get_db_connection()
        log_action(conn, user_id, 'LOGOUT', 'User logged out', request.remote_addr)
        conn.commit()
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
        session.clear() # 强制重新登录
        return success(message='密码修改成功，请重新登录')
    else:
        return fail('旧密码不正确', 400)
