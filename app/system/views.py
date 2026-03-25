from flask import Blueprint, request, session, current_app, send_from_directory, jsonify
from app.utils.db import get_db_connection
from app.utils.response import success, fail
from app.utils.auth import login_required, role_required, get_permission_mode
from config import get_config
import sqlite3
import os
import json
import shutil
from datetime import datetime

config = get_config()
ROLES = config.ROLES

system_bp = Blueprint('system', __name__, url_prefix='/api')

@system_bp.route('/announcements', methods=['GET'])
def get_announcements():
    conn = get_db_connection()
    try:
        announcements = conn.execute('''
            SELECT a.*, u.real_name as author_name 
            FROM announcements a 
            LEFT JOIN users u ON a.created_by = u.id 
            ORDER BY a.created_at DESC
        ''').fetchall()
        return success(data=[dict(row) for row in announcements])
    except sqlite3.OperationalError:
        return success(data=[])

@system_bp.route('/announcements', methods=['POST'])
@login_required
@role_required([ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN']])
def create_announcement():
    user_id = session.get('user_id')
    data = request.json
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO announcements (title, content, type, created_by)
            VALUES (?, ?, ?, ?)
        ''', (data.get('title'), data.get('content'), data.get('type', 'news'), user_id))
        
        users = conn.execute('SELECT id FROM users WHERE id != ?', (user_id,)).fetchall()
        for u in users:
            conn.execute('INSERT INTO notifications (user_id, title, content, type) VALUES (?, ?, ?, ?)',
                        (u['id'], '新公告发布', f"系统发布了新公告：{data.get('title')}", 'info'))
            
        conn.commit()
        return success(message='发布成功')
    except Exception as e:
        return fail(str(e), 500)

@system_bp.route('/announcements/<int:aid>', methods=['DELETE'])
@login_required
@role_required([ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN']])
def delete_announcement(aid):
    user_id = session.get('user_id')
    role = session.get('role')
    conn = get_db_connection()
    try:
        row = conn.execute('SELECT id, created_by FROM announcements WHERE id = ?', (aid,)).fetchone()
        if not row:
            return fail('公告不存在', 404)

        if role != ROLES['SYSTEM_ADMIN'] and row['created_by'] != user_id:
            return fail('无权限删除他人公告', 403)

        conn.execute('DELETE FROM announcements WHERE id = ?', (aid,))
        conn.commit()
        return success(message='删除成功')
    except sqlite3.OperationalError:
        return fail('公告表不存在', 500)
    except Exception as e:
        return fail(str(e), 500)

@system_bp.route('/competitions', methods=['GET'])
def get_competitions():
    conn = get_db_connection()
    try:
        competitions = conn.execute('''
            SELECT * FROM competitions 
            ORDER BY CASE status 
                WHEN 'active' THEN 1 
                WHEN 'upcoming' THEN 2 
                WHEN 'ended' THEN 3 
                ELSE 4 END, 
            created_at DESC
        ''').fetchall()
        
        user_id = session.get('user_id')
        res = [dict(row) for row in competitions]
        
        if user_id and session.get('role') == ROLES['STUDENT']:
            user_projects = conn.execute('SELECT competition_id, id, status FROM projects WHERE created_by = ? AND competition_id IS NOT NULL', (user_id,)).fetchall()
            project_map = {row['competition_id']: {'id': row['id'], 'status': row['status']} for row in user_projects}
            
            for comp in res:
                if comp['id'] in project_map:
                    comp['is_registered'] = True
                    comp['project_id'] = project_map[comp['id']]['id']
                    comp['project_status'] = project_map[comp['id']]['status']
                else:
                    comp['is_registered'] = False
        return success(data=res)
    except sqlite3.OperationalError:
        return success(data=[])

@system_bp.route('/competitions', methods=['POST'])
@login_required
@role_required([ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN']])
def create_competition():
    data = request.json or {}
    conn = get_db_connection()
    try:
        try:
            conn.execute('SELECT form_config FROM competitions LIMIT 1')
        except sqlite3.OperationalError:
            conn.execute('ALTER TABLE competitions ADD COLUMN form_config TEXT')
        try:
            conn.execute('SELECT template_type FROM competitions LIMIT 1')
        except sqlite3.OperationalError:
            conn.execute("ALTER TABLE competitions ADD COLUMN template_type TEXT DEFAULT 'default'")

        form_config = data.get('form_config')
        if isinstance(form_config, (dict, list)):
            form_config = json.dumps(form_config, ensure_ascii=False)

        conn.execute('''
            INSERT INTO competitions (title, level, system_type, competition_level, national_organizer, school_organizer, organizer, registration_start, registration_end, description, status, template_type, form_config)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('title'),
            data.get('level', 'School'),
            data.get('system_type'),
            data.get('competition_level'),
            data.get('national_organizer'),
            data.get('school_organizer'),
            data.get('organizer'),
            data.get('registration_start'),
            data.get('registration_end'),
            data.get('description'),
            data.get('status', 'active'),
            data.get('template_type', 'default'),
            form_config
        ))
        conn.commit()
        return success(message='发布成功')
    except Exception as e:
        return fail(str(e), 500)

@system_bp.route('/competitions/<int:cid>', methods=['PUT'])
@login_required
@role_required([ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN']])
def update_competition(cid):
    data = request.json or {}
    conn = get_db_connection()
    try:
        form_config = data.get('form_config')
        if isinstance(form_config, (dict, list)):
            form_config = json.dumps(form_config, ensure_ascii=False)

        conn.execute('''
            UPDATE competitions
            SET title=?, level=?, system_type=?, competition_level=?, national_organizer=?, school_organizer=?, organizer=?, registration_start=?, registration_end=?, description=?, status=?, template_type=?, form_config=?
            WHERE id=?
        ''', (
            data.get('title'),
            data.get('level'),
            data.get('system_type'),
            data.get('competition_level'),
            data.get('national_organizer'),
            data.get('school_organizer'),
            data.get('organizer'),
            data.get('registration_start'),
            data.get('registration_end'),
            data.get('description'),
            data.get('status'),
            data.get('template_type', 'default'),
            form_config,
            cid
        ))
        conn.commit()
        return success(message='更新成功')
    except Exception as e:
        return fail(str(e), 500)

@system_bp.route('/competitions/<int:cid>', methods=['DELETE'])
@login_required
@role_required([ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN']])
def delete_competition(cid):
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM competitions WHERE id = ?', (cid,))
        conn.commit()
        return success(message='删除成功')
    except Exception as e:
        return fail(str(e), 500)

@system_bp.route('/stats', methods=['GET'])
@login_required
@role_required([ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN']])
def get_stats():
    conn = get_db_connection()
    try:
        status_stats = conn.execute('SELECT status, COUNT(*) as count FROM projects GROUP BY status').fetchall()
        role_stats = conn.execute('SELECT role, COUNT(*) as count FROM users GROUP BY role').fetchall()
        college_stats = conn.execute('SELECT college, COUNT(*) as count FROM projects GROUP BY college').fetchall()
        
        return success(data={
            'project_stats': [dict(row) for row in status_stats],
            'user_stats': [dict(row) for row in role_stats],
            'college_stats': [dict(row) for row in college_stats]
        })
    except Exception as e:
        return fail(str(e), 500)

@system_bp.route('/logs', methods=['GET'])
@login_required
@role_required([ROLES['SYSTEM_ADMIN']])
def get_logs():
    limit = request.args.get('limit', 100)
    conn = get_db_connection()
    logs = conn.execute(f'''
        SELECT l.*, u.username, u.real_name 
        FROM system_logs l
        LEFT JOIN users u ON l.user_id = u.id
        ORDER BY l.created_at DESC LIMIT {limit}
    ''').fetchall()
    return success(data=[dict(l) for l in logs])

@system_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@role_required([ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN']])
def manage_settings():
    conn = get_db_connection()
    if request.method == 'GET':
        settings = conn.execute('SELECT * FROM system_settings').fetchall()
        return success(data={row['key']: row['value'] for row in settings})
    else:
        data = request.json
        try:
            if isinstance(data, dict) and 'permission_mode' in data:
                if session.get('role') != ROLES['SYSTEM_ADMIN']:
                    return fail('只有系统管理员可修改权限模式', 403)

                new_mode_raw = data.get('permission_mode')
                mode_map = {
                    'mixed': 'mixed',
                    'strict': 'strict',
                    '混合': 'mixed',
                    '严格': 'strict',
                    '混合模式': 'mixed',
                    '严格模式': 'strict'
                }
                new_mode = mode_map.get(str(new_mode_raw).strip(), None)
                if new_mode not in ['mixed', 'strict']:
                    return fail('无效的权限模式', 400)

                old_mode = get_permission_mode()
                if old_mode != new_mode:
                    conn.execute(
                        'INSERT INTO system_logs (user_id, action, details, ip_address) VALUES (?, ?, ?, ?)',
                        (
                            session.get('user_id'),
                            'PERMISSION_MODE_CHANGED',
                            json.dumps({'old_mode': old_mode, 'new_mode': new_mode}, ensure_ascii=False),
                            request.remote_addr
                        )
                    )

            for key, value in data.items():
                exists = conn.execute('SELECT key FROM system_settings WHERE key = ?', (key,)).fetchone()
                if exists:
                    conn.execute('UPDATE system_settings SET value = ? WHERE key = ?', (value, key))
                else:
                    conn.execute('INSERT INTO system_settings (key, value) VALUES (?, ?)', (key, value))
            conn.commit()
            return success(message='设置已更新')
        except Exception as e:
            conn.rollback()
            return fail(str(e), 500)

@system_bp.route('/permission-mode', methods=['GET'])
@login_required
def get_permission_mode_api():
    return success(data={'mode': get_permission_mode()})

@system_bp.route('/meta/colleges', methods=['GET'])
@login_required
def meta_colleges():
    conn = get_db_connection()
    colleges = set()
    try:
        rows = conn.execute('SELECT DISTINCT college FROM users WHERE college IS NOT NULL AND college != ""').fetchall()
        for r in rows:
            colleges.add(r['college'])
    except Exception:
        pass
    try:
        rows = conn.execute('SELECT DISTINCT college FROM projects WHERE college IS NOT NULL AND college != ""').fetchall()
        for r in rows:
            colleges.add(r['college'])
    except Exception:
        pass
    return success(data=sorted(colleges))

@system_bp.route('/meta/departments', methods=['GET'])
@login_required
def meta_departments():
    conn = get_db_connection()
    depts = set()
    try:
        rows = conn.execute('SELECT DISTINCT department FROM users WHERE department IS NOT NULL AND department != ""').fetchall()
        for r in rows:
            depts.add(r['department'])
    except Exception:
        pass
    try:
        rows = conn.execute('SELECT DISTINCT department FROM projects WHERE department IS NOT NULL AND department != ""').fetchall()
        for r in rows:
            depts.add(r['department'])
    except Exception:
        pass
    return success(data=sorted(depts))

@system_bp.route('/backup', methods=['POST'])
@login_required
@role_required([ROLES['SYSTEM_ADMIN']])
def create_backup():
    try:
        src = config.DB_PATH
        if not os.path.exists(src):
            return fail('数据库文件不存在', 500)
            
        backups_dir = os.path.join(os.path.dirname(src), 'backups')
        os.makedirs(backups_dir, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d-%H%M%S')
        dst = os.path.join(backups_dir, f'database-{ts}.db')
        shutil.copyfile(src, dst)
        return success(data={'filename': os.path.basename(dst)}, message='备份成功')
    except Exception as e:
        return fail(f'备份失败: {str(e)}', 500)

@system_bp.route('/notifications', methods=['GET'])
@login_required
def get_notifications():
    user_id = session.get('user_id')
    conn = get_db_connection()
    notifications = conn.execute('SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC', (user_id,)).fetchall()
    return success(data=[dict(row) for row in notifications])

@system_bp.route('/notifications/<int:nid>/read', methods=['PUT'])
@login_required
def read_notification(nid):
    user_id = session.get('user_id')
    conn = get_db_connection()
    conn.execute('UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?', (nid, user_id))
    conn.commit()
    return success(message='已读')
