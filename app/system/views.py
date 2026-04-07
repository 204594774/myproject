from flask import Blueprint, request, session, current_app, send_from_directory, jsonify, Response
from app.utils.db import get_db_connection
from app.utils.response import success, fail
from app.utils.auth import login_required, role_required, get_permission_mode, get_auth_context
from config import get_config
import sqlite3
import os
import json
import shutil
import time
import uuid
import re
from datetime import datetime
import csv
import io

config = get_config()
ROLES = config.ROLES

system_bp = Blueprint('system', __name__, url_prefix='/api')

@system_bp.route('/common/upload', methods=['POST'])
def common_upload():
    if 'file' not in request.files:
        return fail('未上传文件', 400)
    file = request.files['file']
    if file.filename == '':
        return fail('文件名为空', 400)
        
    if file:
        ext = os.path.splitext(file.filename)[1]
        filename = f"{int(time.time())}_{uuid.uuid4().hex[:8]}{ext}"
        
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        return jsonify({
            'code': 200,
            'message': '上传成功', 
            'data': {
                'url': f'/static/uploads/{filename}',
                'filename': filename
            }
        })
    return fail('上传失败', 500)

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
@login_required
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
        role = session.get('role')
        if not user_id or not role:
            ctx = get_auth_context()
            if ctx:
                user_id = user_id or ctx.get('user_id')
                role = role or ctx.get('role')
        res = [dict(row) for row in competitions]
        
        if user_id and role == ROLES['STUDENT']:
            u = conn.execute('SELECT identity_number, real_name FROM users WHERE id = ?', (user_id,)).fetchone()
            sid = (u['identity_number'] if u else '') or ''
            rn = (u['real_name'] if u else '') or ''
            if sid:
                user_projects = conn.execute(
                    '''
                    SELECT DISTINCT p.competition_id, p.id, p.status, p.created_by
                    FROM projects p
                    LEFT JOIN project_members pm ON pm.project_id = p.id
                    WHERE p.competition_id IS NOT NULL
                      AND (p.created_by = ? OR pm.student_id = ?)
                    ORDER BY p.id DESC
                    ''',
                    (user_id, sid)
                ).fetchall()
            else:
                user_projects = conn.execute(
                    '''
                    SELECT DISTINCT p.competition_id, p.id, p.status, p.created_by
                    FROM projects p
                    LEFT JOIN project_members pm ON pm.project_id = p.id
                    WHERE p.competition_id IS NOT NULL
                      AND (p.created_by = ? OR (pm.name = ? AND COALESCE(pm.student_id,'') = ''))
                    ORDER BY p.id DESC
                    ''',
                    (user_id, rn)
                ).fetchall()
            project_map = {}
            for row in user_projects:
                cid = row['competition_id']
                if cid is None:
                    continue
                if cid in project_map:
                    continue
                project_map[cid] = {'id': row['id'], 'status': row['status'], 'created_by': row['created_by']}
            
            for comp in res:
                if comp['id'] in project_map:
                    comp['is_registered'] = True
                    comp['project_id'] = project_map[comp['id']]['id']
                    comp['project_status'] = project_map[comp['id']]['status']
                    comp['is_leader'] = int(project_map[comp['id']].get('created_by') or 0) == int(user_id)
                else:
                    comp['is_registered'] = False
                    comp['is_leader'] = False
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
@role_required([ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN'], ROLES['SCHOOL_APPROVER'], ROLES['COLLEGE_APPROVER']])
def get_stats():
    conn = get_db_connection()
    try:
        status_stats = conn.execute('SELECT status, COUNT(*) as count FROM projects GROUP BY status').fetchall()
        role_stats = conn.execute('SELECT role, COUNT(*) as count FROM users GROUP BY role').fetchall()
        college_stats = conn.execute('SELECT college, COUNT(*) as count FROM projects GROUP BY college').fetchall()
        type_stats = conn.execute('SELECT project_type, COUNT(*) as count FROM projects GROUP BY project_type').fetchall()
        
        # --- 大挑 (Challenge Cup) 专属统计 ---
        challenge_cup_stats = conn.execute("SELECT status, COUNT(*) as count FROM projects WHERE project_type = 'challenge_cup' GROUP BY status").fetchall()
        challenge_cup_total = sum(row['count'] for row in challenge_cup_stats)
        challenge_cup_approved = sum(row['count'] for row in challenge_cup_stats if row['status'] in ['school_approved', 'finished'])
        
        challenge_stats_data = {
            'total_applications': challenge_cup_total,
            'pass_rate': f"{(challenge_cup_approved / challenge_cup_total * 100):.2f}%" if challenge_cup_total > 0 else "0%",
            'status_distribution': [dict(row) for row in challenge_cup_stats]
        }
        
        return success(data={
            'project_stats': [dict(row) for row in status_stats],
            'user_stats': [dict(row) for row in role_stats],
            'college_stats': [dict(row) for row in college_stats],
            'type_stats': [dict(row) for row in type_stats],
            'challenge_cup_stats': challenge_stats_data
        })
    except Exception as e:
        return fail(str(e), 500)


@system_bp.route('/reports/export', methods=['GET'])
@login_required
@role_required([ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN'], ROLES['SCHOOL_APPROVER'], ROLES['COLLEGE_APPROVER']])
def export_projects_report():
    user_id = session.get('user_id')
    role = session.get('role')
    conn = get_db_connection()
    try:
        query = "SELECT * FROM projects WHERE 1=1"
        params = []
        if role == ROLES['COLLEGE_APPROVER']:
            current_user = conn.execute('SELECT college FROM users WHERE id = ?', (user_id,)).fetchone()
            if current_user and current_user['college']:
                query += " AND college = ?"
                params.append(current_user['college'])
        query += " ORDER BY created_at DESC"
        projects = conn.execute(query, params).fetchall()
        
        import io
        import csv
        output = io.StringIO()
        writer = csv.writer(output)
        headers = ['ID', 'Title', 'Leader', 'Advisor', 'College', 'Department', 'Type', 'Level', 'Status', 'Year', 'Created At']
        writer.writerow(headers)
        for row in projects:
            writer.writerow([
                row['id'],
                row['title'],
                row['leader_name'],
                row['advisor_name'],
                row['college'],
                row['department'],
                row['project_type'],
                row['level'],
                row['status'],
                row['year'],
                row['created_at']
            ])
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-disposition": "attachment; filename=projects_report.csv"}
        )
    except Exception as e:
        return fail(str(e), 500)
    finally:
        conn.close()

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

@system_bp.route('/logs/export', methods=['GET'])
@login_required
@role_required([ROLES['SYSTEM_ADMIN']])
def export_logs():
    action_prefix = (request.args.get('action_prefix') or '').strip()
    limit = int(request.args.get('limit', 5000))
    if limit <= 0:
        limit = 5000
    if limit > 20000:
        limit = 20000
    conn = get_db_connection()
    try:
        q = '''
            SELECT l.id, l.created_at, l.action, l.details, l.ip_address, u.username, u.real_name
            FROM system_logs l
            LEFT JOIN users u ON l.user_id = u.id
            WHERE 1=1
        '''
        params = []
        if action_prefix:
            q += ' AND l.action LIKE ?'
            params.append(f"{action_prefix}%")
        q += ' ORDER BY l.created_at DESC LIMIT ?'
        params.append(limit)
        rows = conn.execute(q, params).fetchall()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Created At', 'Action', 'Details', 'IP', 'Username', 'Real Name'])
        for r in rows:
            writer.writerow([
                r['id'],
                r['created_at'],
                r['action'],
                r['details'],
                r['ip_address'],
                r['username'],
                r['real_name']
            ])
        output.seek(0)
        fn = 'system_logs.csv' if not action_prefix else f'system_logs_{action_prefix}.csv'
        return Response(output.getvalue(), mimetype='text/csv', headers={'Content-disposition': f'attachment; filename={fn}'})
    except Exception as e:
        return fail(str(e), 500)

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

@system_bp.route('/system/backup', methods=['POST'])
@login_required
@role_required([ROLES['SYSTEM_ADMIN']])
def create_backup_compat():
    try:
        src = config.DB_PATH
        if not os.path.exists(src):
            return fail('数据库文件不存在', 500)

        backups_dir = os.path.join(os.path.dirname(src), 'backups')
        os.makedirs(backups_dir, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d-%H%M%S')
        filename = f'database-{ts}.db'
        dst = os.path.join(backups_dir, filename)
        shutil.copyfile(src, dst)
        return jsonify({'message': '备份成功', 'path': f'/api/backups/{filename}'})
    except Exception as e:
        return fail(f'备份失败: {str(e)}', 500)

@system_bp.route('/backups/<path:filename>', methods=['GET'])
@login_required
@role_required([ROLES['SYSTEM_ADMIN']])
def download_backup(filename):
    src = config.DB_PATH
    backups_dir = os.path.join(os.path.dirname(src), 'backups')
    full_path = os.path.join(backups_dir, filename)
    if not os.path.exists(full_path):
        return fail('文件不存在', 404)
    return send_from_directory(backups_dir, filename, as_attachment=True)

@system_bp.route('/notifications', methods=['GET'])
@login_required
def get_notifications():
    user_id = session.get('user_id')
    role = session.get('role')
    conn = get_db_connection()

    try:
        if role == ROLES['STUDENT']:
            rows = conn.execute(
                '''
                SELECT
                    p.id, p.title, p.status, p.current_level, p.review_stage, p.school_review_result,
                    p.project_type, c.template_type AS competition_template_type, c.title AS competition_title
                FROM projects p
                LEFT JOIN competitions c ON p.competition_id = c.id
                WHERE p.created_by = ?
                ''',
                (user_id,)
            ).fetchall()
            for r in rows:
                p = dict(r)
                tpl_key = str(p.get('competition_template_type') or '').strip()
                ptype = str(p.get('project_type') or '').strip()
                ctitle = str(p.get('competition_title') or '').strip()
                is_challenge = (ptype == 'challenge_cup') or (tpl_key in ['challenge_cup', 'da_tiao']) or ('挑战杯' in ctitle and '课外学术科技作品竞赛' in ctitle)
                if not is_challenge:
                    continue
                pid = int(p.get('id') or 0)
                title_txt = str(p.get('title') or '').strip() or f'项目ID {pid}'
                st = str(p.get('status') or '').strip()
                lv = str(p.get('current_level') or '').strip()
                stage = str(p.get('review_stage') or '').strip()
                
                def ensure(title, content):
                    exists = conn.execute(
                        'SELECT 1 FROM notifications WHERE user_id = ? AND title = ? AND content LIKE ? LIMIT 1',
                        (user_id, title, f'%《{title_txt}》%')
                    ).fetchone()
                    if exists:
                        return
                    meta = None
                    try:
                        meta = json.dumps({'route': f'/project/{pid}', 'project_id': pid}, ensure_ascii=False)
                    except Exception:
                        meta = None
                    try:
                        conn.execute(
                            'INSERT INTO notifications (user_id, title, content, type, meta) VALUES (?, ?, ?, ?, ?)',
                            (user_id, title, content, 'project', meta)
                        )
                    except Exception:
                        conn.execute(
                            'INSERT INTO notifications (user_id, title, content, type) VALUES (?, ?, ?, ?)',
                            (user_id, title, content, 'project')
                        )
                
                if st == 'pending_college_recommendation':
                    ensure('学院赛评审已完成', f'您的项目《{title_txt}》学院赛评审已完成，当前状态：待学院确认推荐。')
                elif st == 'pending_school_recommendation':
                    ensure('校赛评审已完成', f'您的项目《{title_txt}》校赛评审已完成，当前状态：待学校确认推荐。')
                elif st == 'school_review' and (lv == 'school' or stage == 'school'):
                    ensure('已推荐至校赛', f'您的项目《{title_txt}》已被确认推荐至校赛，请关注后续评审安排。')
                elif st in ['provincial_review', 'provincial'] or (lv == 'provincial' or stage == 'provincial') or str(p.get('school_review_result') or '').strip() == 'approved':
                    ensure('已推荐至省赛', f'您的项目《{title_txt}》已被确认推荐至省赛，请关注后续评审安排。')
            
            conn.commit()
    except Exception:
        try:
            conn.execute('ROLLBACK')
        except Exception:
            pass
    if role == ROLES['TEACHER']:
        me = conn.execute('SELECT real_name FROM users WHERE id = ?', (user_id,)).fetchone()
        rn = str((me['real_name'] if me else '') or '').strip()
        if rn:
            rows = conn.execute(
                'SELECT id FROM users WHERE role = ? AND TRIM(real_name) = TRIM(?)',
                (ROLES['TEACHER'], rn)
            ).fetchall()
            ids = [int(r['id']) for r in rows if r and r['id'] is not None]
            if ids:
                placeholders = ','.join(['?'] * len(ids))
                notifications = conn.execute(
                    f'SELECT * FROM notifications WHERE user_id IN ({placeholders}) ORDER BY created_at DESC',
                    ids
                ).fetchall()
            else:
                notifications = []
        else:
            notifications = []
    else:
        notifications = conn.execute('SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC', (user_id,)).fetchall()

    def infer_meta(title, content):
        t = str(title or '').strip()
        c = str(content or '').strip()
        if not (t or c):
            return None
        is_review_task_msg = ('评审任务' in t) or ('评审任务' in c)
        is_experience_audit_msg = ('待导师审核经验内容' in t) or ('待学校审核经验内容' in t) or ('待导师审核经验内容' in c) or ('待学校审核经验内容' in c)
        is_audit_msg = ('请审核' in t) or ('请审核' in c) or ('请评审' in t) or ('请评审' in c) or ('待审核' in t) or ('待审核' in c) or ('待评审' in t) or ('待评审' in c) or ('待学院审核' in t) or ('待学院审核' in c) or ('待学校审核' in t) or ('待学校审核' in c) or is_experience_audit_msg
        if ('借鉴' in t) or ('经验库' in t) or ('借鉴' in c) or ('经验库' in c):
            return {'route': '/legacy'}
        if (('经验内容' in t) or ('经验内容' in c)) and not is_audit_msg:
            return {'route': '/legacy'}
        m = re.search(r'项目《([^》]{1,200})》', c)
        proj_title = (m.group(1).strip() if m else '')
        if not proj_title:
            m2 = re.search(r'项目[:：]\\s*([^，。\\n]{1,200})', c)
            proj_title = (m2.group(1).strip() if m2 else '')
        if proj_title:
            p = conn.execute(
                'SELECT id FROM projects WHERE title = ? ORDER BY id DESC LIMIT 1',
                (proj_title,)
            ).fetchone()
            if not p and len(proj_title) >= 3:
                p = conn.execute(
                    'SELECT id FROM projects WHERE title LIKE ? ORDER BY id DESC LIMIT 1',
                    (f'%{proj_title}%',)
                ).fetchone()
            if p:
                pid = int(p['id'])
                if is_review_task_msg:
                    return {'route': '/', 'query': {'tab': 'my_reviews', 'task': 'review_task', 'pid': pid}, 'project_id': pid}
                if is_audit_msg:
                    if role == ROLES['SCHOOL_APPROVER']:
                        return {'route': '/', 'query': {'tab': 'my_reviews', 'task': 'experience_review_school', 'pid': pid}, 'project_id': pid}
                    return {'route': '/', 'query': {'tab': 'my_reviews', 'task': 'experience_review_teacher', 'pid': pid}, 'project_id': pid}
                return {'route': f'/project/{pid}', 'project_id': pid}
        if is_review_task_msg:
            return {'route': '/', 'query': {'tab': 'my_reviews'}}
        if is_audit_msg:
            return {'route': '/', 'query': {'tab': 'my_reviews'}}
        return None

    out = []
    for r in notifications:
        d = dict(r)
        meta_raw = d.get('meta')
        meta_obj = None
        meta_valid = False
        if isinstance(meta_raw, dict):
            meta_obj = meta_raw
            meta_valid = bool(str(meta_obj.get('route') or '').strip())
        elif isinstance(meta_raw, str) and meta_raw.strip():
            try:
                parsed = json.loads(meta_raw)
                if isinstance(parsed, dict):
                    meta_obj = parsed
                    meta_valid = bool(str(meta_obj.get('route') or '').strip())
            except Exception:
                meta_obj = None
                meta_valid = False

        if meta_valid:
            try:
                t0 = str(d.get('title') or '').strip()
                c0 = str(d.get('content') or '').strip()
                is_audit_msg = ('请审核' in t0) or ('请审核' in c0) or ('待审核' in t0) or ('待审核' in c0) or ('待导师审核经验内容' in t0) or ('待学校审核经验内容' in t0) or ('待导师审核经验内容' in c0) or ('待学校审核经验内容' in c0)
                if is_audit_msg and isinstance(meta_obj, dict):
                    r0 = str(meta_obj.get('route') or '').strip()
                    q0 = meta_obj.get('query') if isinstance(meta_obj.get('query'), dict) else {}
                    if (r0 == '/legacy' or r0.startswith('/project/')) and str(q0.get('tab') or '').strip() != 'my_reviews':
                        pid = meta_obj.get('project_id')
                        if not pid:
                            m3 = re.search(r'/project/(\d+)', r0)
                            pid = int(m3.group(1)) if m3 else 0
                        if pid:
                            task = 'experience_review_school' if role == ROLES['SCHOOL_APPROVER'] else 'experience_review_teacher'
                            meta_obj = {'route': '/', 'query': {'tab': 'my_reviews', 'task': task, 'pid': int(pid)}, 'project_id': int(pid)}
                            meta_valid = True
            except Exception:
                meta_valid = meta_valid

        if not meta_valid:
            inferred = infer_meta(d.get('title'), d.get('content'))
            if inferred:
                meta_obj = inferred
                meta_valid = True
            elif isinstance(meta_raw, str) and meta_raw.strip():
                d['meta'] = ''

        if meta_obj and isinstance(meta_obj, dict) and meta_valid:
            try:
                d['meta'] = json.dumps(meta_obj, ensure_ascii=False)
            except Exception:
                d['meta'] = d.get('meta')
        out.append(d)
    return success(data=out)

@system_bp.route('/notifications/export', methods=['GET'])
@login_required
def export_notifications():
    user_id = session.get('user_id')
    role = session.get('role')
    conn = get_db_connection()

    export_user_id = user_id
    try:
        req_user_id = request.args.get('user_id')
        if role == ROLES['SYSTEM_ADMIN'] and str(req_user_id or '').strip():
            export_user_id = int(req_user_id)
    except Exception:
        export_user_id = user_id

    rows = conn.execute(
        'SELECT id, title, content, type, is_read, created_at FROM notifications WHERE user_id = ? ORDER BY created_at DESC',
        (export_user_id,),
    ).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', '标题', '内容', '类型', '已读', '时间'])
    for r in rows:
        d = dict(r)
        writer.writerow([
            d.get('id'),
            d.get('title') or '',
            d.get('content') or '',
            d.get('type') or '',
            1 if int(d.get('is_read') or 0) == 1 else 0,
            d.get('created_at') or '',
        ])
    csv_text = output.getvalue()
    output.close()

    data = '\ufeff' + csv_text
    ts = datetime.now().strftime('%Y%m%d-%H%M%S')
    filename = f'notifications-{export_user_id}-{ts}.csv'
    return Response(
        data,
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename={filename}'},
    )

@system_bp.route('/notifications/<int:nid>/read', methods=['PUT'])
@login_required
def read_notification(nid):
    user_id = session.get('user_id')
    role = session.get('role')
    conn = get_db_connection()
    if role == ROLES['TEACHER']:
        me = conn.execute('SELECT real_name FROM users WHERE id = ?', (user_id,)).fetchone()
        rn = str((me['real_name'] if me else '') or '').strip()
        if rn:
            rows = conn.execute(
                'SELECT id FROM users WHERE role = ? AND TRIM(real_name) = TRIM(?)',
                (ROLES['TEACHER'], rn)
            ).fetchall()
            ids = [int(r['id']) for r in rows if r and r['id'] is not None]
            if ids:
                placeholders = ','.join(['?'] * len(ids))
                conn.execute(
                    f'UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id IN ({placeholders})',
                    [nid] + ids
                )
        else:
            conn.execute('UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?', (nid, user_id))
    else:
        conn.execute('UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?', (nid, user_id))
    conn.commit()
    return success(message='已读')

@system_bp.route('/jiebang/topics', methods=['GET'])
def get_jiebang_topics():
    year = request.args.get('year', 2026)
    try:
        year = int(year)
    except Exception:
        year = 2026
    enabled = request.args.get('enabled', '')
    enabled_filter = None
    if str(enabled).strip() != '':
        try:
            enabled_filter = 1 if str(enabled).strip() in ['1', 'true', 'True'] else 0
        except Exception:
            enabled_filter = None

    conn = get_db_connection()
    try:
        sql = 'SELECT * FROM jiebang_topics WHERE year = ?'
        params = [year]
        if enabled_filter is not None:
            sql += ' AND enabled = ?'
            params.append(enabled_filter)
        sql += ' ORDER BY group_no, topic_no, id'
        rows = conn.execute(sql, params).fetchall()
        return success(data=[dict(r) for r in rows])
    except Exception as e:
        return fail(str(e), 500)

@system_bp.route('/jiebang/topics/tree', methods=['GET'])
def get_jiebang_topics_tree():
    year = request.args.get('year', 2026)
    try:
        year = int(year)
    except Exception:
        year = 2026

    conn = get_db_connection()
    try:
        rows = conn.execute(
            'SELECT * FROM jiebang_topics WHERE year = ? AND enabled = 1 ORDER BY group_no, topic_no, id',
            (year,)
        ).fetchall()
        groups = []
        group_map = {}
        for r in rows:
            d = dict(r)
            gkey = f"{d.get('group_no')}::{d.get('group_name')}"
            if gkey not in group_map:
                g = {
                    'group_no': d.get('group_no'),
                    'group_name': d.get('group_name'),
                    'topics': []
                }
                group_map[gkey] = g
                groups.append(g)
            group_map[gkey]['topics'].append({
                'id': d.get('id'),
                'topic_no': d.get('topic_no'),
                'topic_title': d.get('topic_title'),
                'topic_desc': d.get('topic_desc')
            })
        return success(data={'year': year, 'groups': groups})
    except Exception as e:
        return fail(str(e), 500)

@system_bp.route('/jiebang/topics', methods=['POST'])
@login_required
@role_required([ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN']])
def create_jiebang_topic():
    data = request.json or {}
    conn = get_db_connection()
    try:
        year = int(data.get('year') or 2026)
        group_no = int(data.get('group_no') or 1)
        group_name = str(data.get('group_name') or '').strip()
        topic_no = int(data.get('topic_no') or 1)
        topic_title = str(data.get('topic_title') or '').strip()
        topic_desc = str(data.get('topic_desc') or '').strip()
        enabled = 1 if str(data.get('enabled') or '1').strip() in ['1', 'true', 'True'] else 0
        if not group_name:
            return fail('group_name 必填', 400)
        if not topic_title:
            return fail('topic_title 必填', 400)
        conn.execute(
            '''
            INSERT INTO jiebang_topics (year, group_no, group_name, topic_no, topic_title, topic_desc, enabled, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''',
            (year, group_no, group_name, topic_no, topic_title, topic_desc, enabled)
        )
        conn.commit()
        return success(message='创建成功')
    except Exception as e:
        conn.rollback()
        return fail(str(e), 500)

@system_bp.route('/jiebang/topics/<int:tid>', methods=['PUT'])
@login_required
@role_required([ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN']])
def update_jiebang_topic(tid):
    data = request.json or {}
    conn = get_db_connection()
    try:
        row = conn.execute('SELECT id FROM jiebang_topics WHERE id = ?', (tid,)).fetchone()
        if not row:
            return fail('记录不存在', 404)
        fields = {}
        for k in ['year', 'group_no', 'group_name', 'topic_no', 'topic_title', 'topic_desc', 'enabled']:
            if k in data:
                fields[k] = data.get(k)
        if 'group_name' in fields:
            fields['group_name'] = str(fields['group_name'] or '').strip()
            if not fields['group_name']:
                return fail('group_name 不能为空', 400)
        if 'topic_title' in fields:
            fields['topic_title'] = str(fields['topic_title'] or '').strip()
            if not fields['topic_title']:
                return fail('topic_title 不能为空', 400)
        if 'topic_desc' in fields:
            fields['topic_desc'] = str(fields['topic_desc'] or '').strip()
        if 'year' in fields:
            fields['year'] = int(fields['year'] or 2026)
        if 'group_no' in fields:
            fields['group_no'] = int(fields['group_no'] or 1)
        if 'topic_no' in fields:
            fields['topic_no'] = int(fields['topic_no'] or 1)
        if 'enabled' in fields:
            fields['enabled'] = 1 if str(fields['enabled']).strip() in ['1', 'true', 'True'] else 0
        if not fields:
            return success(message='无更新')
        set_sql = ', '.join([f"{k} = ?" for k in fields.keys()] + ['updated_at = CURRENT_TIMESTAMP'])
        params = list(fields.values()) + [tid]
        conn.execute(f'UPDATE jiebang_topics SET {set_sql} WHERE id = ?', params)
        conn.commit()
        return success(message='更新成功')
    except Exception as e:
        conn.rollback()
        return fail(str(e), 500)

@system_bp.route('/jiebang/topics/<int:tid>', methods=['DELETE'])
@login_required
@role_required([ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN']])
def delete_jiebang_topic(tid):
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM jiebang_topics WHERE id = ?', (tid,))
        conn.commit()
        return success(message='删除成功')
    except Exception as e:
        conn.rollback()
        return fail(str(e), 500)
