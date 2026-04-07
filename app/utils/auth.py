from functools import wraps
from flask import session, g, request
from config import get_config
from .response import fail
from .db import get_db_connection
import json
import uuid
from datetime import datetime, timedelta

config = get_config()

TOKEN_HEADER = 'X-Auth-Token'

def _now_str():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def _parse_dt(s):
    try:
        return datetime.strptime(str(s), '%Y-%m-%d %H:%M:%S')
    except Exception:
        return None

def get_request_token():
    t = (request.headers.get(TOKEN_HEADER) or '').strip()
    if t:
        return t
    authz = (request.headers.get('Authorization') or '').strip()
    if authz.lower().startswith('bearer '):
        return authz.split(' ', 1)[1].strip()
    return ''

def _load_token_session(token):
    if not token:
        return None
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM auth_tokens WHERE token = ?', (token,)).fetchone()
    if not row:
        return None
    expires_at = _parse_dt(row['expires_at']) if row['expires_at'] else None
    if expires_at and expires_at <= datetime.now():
        try:
            conn.execute('DELETE FROM auth_tokens WHERE token = ?', (token,))
            conn.commit()
        except Exception:
            pass
        return None
    try:
        conn.execute('UPDATE auth_tokens SET last_seen_at = ? WHERE token = ?', (_now_str(), token))
        conn.commit()
    except Exception:
        pass
    roles = []
    try:
        roles = json.loads(row['all_roles'] or '[]')
    except Exception:
        roles = []
    if not roles and row['active_role']:
        roles = [row['active_role']]
    return {
        'mode': 'token',
        'token': token,
        'user_id': row['user_id'],
        'role': row['active_role'],
        'roles': roles,
        'college': row['college'] or ''
    }

def issue_auth_token(user_id, active_role, roles, college='', ttl_days=7):
    token = uuid.uuid4().hex
    now = datetime.now()
    expires = now + timedelta(days=ttl_days)
    conn = get_db_connection()
    conn.execute(
        '''
        INSERT INTO auth_tokens (token, user_id, active_role, all_roles, college, created_at, last_seen_at, expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            token,
            int(user_id),
            str(active_role),
            json.dumps(list(roles or []), ensure_ascii=False),
            str(college or ''),
            now.strftime('%Y-%m-%d %H:%M:%S'),
            now.strftime('%Y-%m-%d %H:%M:%S'),
            expires.strftime('%Y-%m-%d %H:%M:%S')
        )
    )
    conn.commit()
    return token

def revoke_auth_token(token):
    if not token:
        return
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM auth_tokens WHERE token = ?', (token,))
        conn.commit()
    except Exception:
        pass

def set_token_active_role(token, role):
    if not token:
        return
    conn = get_db_connection()
    conn.execute('UPDATE auth_tokens SET active_role = ?, last_seen_at = ? WHERE token = ?', (str(role), _now_str(), token))
    conn.commit()

def _bind_session_from_ctx(ctx):
    if not ctx:
        return
    session['user_id'] = ctx.get('user_id')
    session['role'] = ctx.get('role')
    session['roles'] = ctx.get('roles', [])
    session['college'] = ctx.get('college', '')
    session.modified = False

def get_auth_context():
    cached = getattr(g, 'auth_ctx', None)
    if cached:
        return cached
    token = get_request_token()
    if token:
        ctx = _load_token_session(token)
        if ctx:
            g.auth_ctx = ctx
            _bind_session_from_ctx(ctx)
            return ctx
    if 'user_id' in session:
        ctx = {
            'mode': 'cookie',
            'token': '',
            'user_id': session.get('user_id'),
            'role': session.get('role'),
            'roles': session.get('roles', []),
            'college': session.get('college', '') or ''
        }
        g.auth_ctx = ctx
        return ctx
    return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        ctx = get_auth_context()
        if not ctx or not ctx.get('user_id'):
            return fail('未登录', 401)
        return f(*args, **kwargs)
    return decorated_function

def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            ctx = get_auth_context()
            role = ctx.get('role') if ctx else None
            if not role or role not in allowed_roles:
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
        ctx = get_auth_context()
        if not ctx or not ctx.get('user_id'):
            return fail('未登录', 401)

        role = ctx.get('role')
        if role == config.ROLES['SYSTEM_ADMIN']:
            return f(*args, **kwargs)

        mode = get_permission_mode()
        if mode == 'strict':
            return fail('当前为严格模式，只有系统管理员可进行用户管理', 403)

        if role in [config.ROLES['PROJECT_ADMIN'], config.ROLES['COLLEGE_APPROVER'], config.ROLES['SCHOOL_APPROVER']]:
            return f(*args, **kwargs)

        return fail('无权限', 403)
    return decorated_function
