from flask import Blueprint, request, session, current_app
from werkzeug.security import generate_password_hash
from app.utils.db import get_db_connection
from app.utils.response import success, fail
from app.utils.auth import user_manage_required
from config import get_config
from flasgger import swag_from
import sqlite3

config = get_config()
ROLES = config.ROLES

users_bp = Blueprint('users', __name__, url_prefix='/api')

@users_bp.route('/users', methods=['GET'])
@user_manage_required
@swag_from({
    'tags': ['用户管理'],
    'summary': '获取用户列表',
    'parameters': [
        {
            'name': 'status',
            'in': 'query',
            'type': 'string',
            'description': '状态过滤 (例如: active, pending)'
        }
    ],
    'responses': {
        200: {'description': '获取成功'}
    }
})
def get_users():
    current_role = session.get('role')
    status_filter = request.args.get('status') # active, pending
    
    conn = get_db_connection()
    try:
        # 检查现有列，兼容旧库
        cols = [r[1] for r in conn.execute('PRAGMA table_info(users)').fetchall()]
        base_cols = ['id', 'username', 'real_name', 'role']
        opt_cols = []
        for c in ['college', 'department', 'identity_number', 'status', 'email', 'phone', 'teaching_office', 'research_area']:
            if c in cols:
                opt_cols.append(c)
        select_cols = ', '.join(base_cols + opt_cols)
        query = f'SELECT {select_cols} FROM users WHERE 1=1'
        params = []
        
        if status_filter and 'status' in cols:
            query += ' AND status = ?'
            params.append(status_filter)
        
        if current_role == ROLES['COLLEGE_APPROVER']:
            query += ' AND college = ?'
            params.append(session.get('college', ''))
            query += ' AND role IN (?, ?)'
            params.extend([ROLES['STUDENT'], ROLES['TEACHER']])
            
        users = conn.execute(query, params).fetchall()
        
        res = []
        for row in users:
            d = dict(row)
            for k in ['college', 'department', 'identity_number', 'status', 'email', 'phone', 'teaching_office', 'research_area']:
                if k not in d:
                    d[k] = ''
                # 如果 status 为空（可能是旧数据或未设置），默认为 active
                if k == 'status' and not d[k]:
                    d[k] = 'active'
            res.append(d)
        return success(data=res)
    except Exception as e:
        return fail(str(e), 500)

@users_bp.route('/users', methods=['POST'])
@user_manage_required
def create_user():
    current_role = session.get('role')
    data = request.json
    new_role = data.get('role')
    
    if current_role in [ROLES['PROJECT_ADMIN'], ROLES['COLLEGE_APPROVER']]:
        if new_role not in [ROLES['TEACHER'], ROLES['STUDENT']]:
            return fail('只能创建导师或学生账号', 403)
            
    conn = get_db_connection()
    try:
        college = data.get('college')
        if current_role == ROLES['COLLEGE_APPROVER']:
            college = session.get('college', '')
            if not college:
                return fail('学院管理员缺少学院信息，无法创建用户', 400)

        hashed_password = generate_password_hash(data.get('password', '123456')) # 默认密码
        conn.execute('''
            INSERT INTO users (username, password, role, real_name, identity_number, department, college, personal_info, teaching_office, research_area)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('username'), 
            hashed_password, 
            new_role,
            data.get('real_name'),
            data.get('identity_number'),
            data.get('department'),
            college,
            data.get('personal_info', ''),
            data.get('teaching_office', ''),
            data.get('research_area', '')
        ))
        conn.commit()
        return success(message='用户创建成功')
    except sqlite3.IntegrityError:
        return fail('用户名已存在', 400)
    except Exception as e:
        return fail(str(e), 500)

@users_bp.route('/users/<int:uid>', methods=['PUT'])
@user_manage_required
def update_user(uid):
    current_role = session.get('role')
    data = request.json
    target_role = data.get('role')
    
    conn = get_db_connection()
    # Check target user exists
    target_user = conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
    if not target_user:
        return fail('用户不存在', 404)
        
    # Permission Check
    if current_role == ROLES['PROJECT_ADMIN']:
        if target_user['role'] == ROLES['SYSTEM_ADMIN']:
            return fail('无权修改系统管理员', 403)
        if target_role and target_role not in [ROLES['STUDENT'], ROLES['TEACHER']]:
            return fail('只能设置为学生或导师角色', 403)
    elif current_role == ROLES['COLLEGE_APPROVER']:
        if (target_user['college'] or '') != (session.get('college', '') or ''):
            return fail('无权修改非本院用户', 403)
        if target_user['role'] not in [ROLES['STUDENT'], ROLES['TEACHER']]:
            return fail('无权修改该用户', 403)
        if 'college' in data and data.get('college') != session.get('college', ''):
            return fail('学院管理员不能修改用户学院', 403)
        if target_role and target_role not in [ROLES['STUDENT'], ROLES['TEACHER']]:
            return fail('只能设置为学生或导师角色', 403)

    try:
        # Build Update Query
        fields = []
        values = []
        
        update_fields = ['real_name', 'identity_number', 'college', 'department', 'teaching_office', 'research_area', 'role', 'status']
        for f in update_fields:
            if f in data:
                fields.append(f'{f} = ?')
                values.append(data[f])
                
        if 'password' in data and data['password']:
            fields.append('password = ?')
            values.append(generate_password_hash(data['password']))
            
        if not fields:
            return success(message='无变更')
            
        values.append(uid)
        conn.execute(f'UPDATE users SET {", ".join(fields)} WHERE id = ?', values)
        conn.commit()
        return success(message='更新成功')
    except Exception as e:
        return fail(str(e), 500)

@users_bp.route('/users/<int:uid>', methods=['DELETE'])
@user_manage_required
def delete_user(uid):
    current_role = session.get('role')
    conn = get_db_connection()
    target_user = conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
    if not target_user:
        return fail('用户不存在', 404)
        
    if current_role == ROLES['PROJECT_ADMIN']:
        if target_user['role'] == ROLES['SYSTEM_ADMIN']:
            return fail('无权删除系统管理员', 403)
    elif current_role == ROLES['COLLEGE_APPROVER']:
        if (target_user['college'] or '') != (session.get('college', '') or ''):
            return fail('无权删除非本院用户', 403)
        if target_user['role'] not in [ROLES['STUDENT'], ROLES['TEACHER']]:
            return fail('无权删除该用户', 403)
            
    try:
        conn.execute('DELETE FROM users WHERE id = ?', (uid,))
        conn.commit()
        return success(message='删除成功')
    except Exception as e:
        return fail(str(e), 500)

@users_bp.route('/users/<int:uid>/approve', methods=['PUT'])
@user_manage_required
def approve_user(uid):
    data = request.json
    action = data.get('action') # approve, reject
    
    conn = get_db_connection()
    current_role = session.get('role')
    if current_role == ROLES['COLLEGE_APPROVER']:
        target_user = conn.execute('SELECT id, college, role FROM users WHERE id = ?', (uid,)).fetchone()
        if not target_user:
            return fail('用户不存在', 404)
        if (target_user['college'] or '') != (session.get('college', '') or ''):
            return fail('无权审核非本院用户', 403)
        if target_user['role'] not in [ROLES['STUDENT'], ROLES['TEACHER']]:
            return fail('无权审核该用户', 403)

    if action == 'approve':
        conn.execute('UPDATE users SET status = "active" WHERE id = ?', (uid,))
    elif action == 'reject':
        conn.execute('UPDATE users SET status = "rejected" WHERE id = ?', (uid,))
    
    conn.commit()
    return success(message='操作成功')
