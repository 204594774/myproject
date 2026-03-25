from functools import wraps
from flask import session, g
from config import get_config
from .response import fail
from .db import get_db_connection

config = get_config()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return fail('未登录', 401)
        return f(*args, **kwargs)
    return decorated_function

def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'role' not in session or session['role'] not in allowed_roles:
                return fail('无权限', 403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_permission_mode():
    cached = getattr(g, 'permission_mode', None)
    if cached:
        return cached

    mode = 'mixed'
    try:
        conn = get_db_connection()
        row = conn.execute('SELECT value FROM system_settings WHERE key = ?', ('permission_mode',)).fetchone()
        if row and row['value']:
            v = str(row['value']).strip().lower()
            if v in ['mixed', 'strict']:
                mode = v
    except Exception:
        mode = 'mixed'

    g.permission_mode = mode
    return mode

def user_manage_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return fail('未登录', 401)

        role = session.get('role')
        if role == config.ROLES['SYSTEM_ADMIN']:
            return f(*args, **kwargs)

        mode = get_permission_mode()
        if mode == 'strict':
            return fail('当前为严格模式，只有系统管理员可进行用户管理', 403)

        if role in [config.ROLES['PROJECT_ADMIN'], config.ROLES['COLLEGE_APPROVER']]:
            return f(*args, **kwargs)

        return fail('无权限', 403)
    return decorated_function
