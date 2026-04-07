from flask import Blueprint, request, session, current_app, Response, send_file
from app.utils.db import get_db_connection
from app.utils.response import success, fail
from app.utils.auth import login_required, role_required
from config import get_config
from flasgger import swag_from
import json
import os
import re
import sqlite3
import shutil
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename

config = get_config()
ROLES = config.ROLES
GHOST_PROJECT_IDS = getattr(config, 'GHOST_PROJECT_IDS', set())
DACHUANG_INNOVATION_COLLEGE_RECOMMEND_DEADLINE = datetime(2026, 4, 30, 23, 59, 59)

projects_bp = Blueprint('projects', __name__, url_prefix='/api')

# Helper for notifications (moved from app.py)
def create_notification(conn, user_id, title, content, n_type='system', meta=None):
    meta_json = None
    try:
        if meta is not None:
            meta_json = json.dumps(meta, ensure_ascii=False)
    except Exception:
        meta_json = None
    try:
        exists = conn.execute(
            "SELECT 1 FROM notifications WHERE user_id = ? AND title = ? AND content = ? AND created_at >= datetime('now','-60 seconds') LIMIT 1",
            (user_id, title, content)
        ).fetchone()
        if exists:
            return
    except Exception:
        pass
    try:
        conn.execute(
            'INSERT INTO notifications (user_id, title, content, type, meta) VALUES (?, ?, ?, ?, ?)',
            (user_id, title, content, n_type, meta_json)
        )
    except sqlite3.OperationalError:
        conn.execute(
            'INSERT INTO notifications (user_id, title, content, type) VALUES (?, ?, ?, ?)',
            (user_id, title, content, n_type)
        )

def resolve_teacher_user_ids(conn, teacher_key):
    key = str(teacher_key or '').strip()
    if not key:
        return []
    try:
        rows = conn.execute(
            '''
            SELECT id
            FROM users
            WHERE role = ?
              AND status = 'active'
              AND (TRIM(real_name) = TRIM(?) OR TRIM(username) = TRIM(?))
            ORDER BY id DESC
            ''',
            (ROLES['TEACHER'], key, key)
        ).fetchall()
        return [int(r['id']) for r in rows if r and r['id'] is not None]
    except Exception:
        return []

def create_role_notifications(conn, role_value, title, content, college=None, exclude_user_id=None, meta=None):
    if college:
        rows = conn.execute('SELECT id FROM users WHERE role = ? AND college = ?', (role_value, college)).fetchall()
    else:
        rows = conn.execute('SELECT id FROM users WHERE role = ?', (role_value,)).fetchall()
    for r in rows:
        uid = r['id']
        if exclude_user_id is not None and int(uid) == int(exclude_user_id):
            continue
        create_notification(conn, uid, title, content, 'approval', meta=meta)

def create_project_related_notifications(conn, project_id, title, content, exclude_user_id=None, include_advisor=True):
    user_ids = set()
    try:
        p = conn.execute(
            'SELECT id, created_by, title, advisor_name FROM projects WHERE id = ?',
            (project_id,)
        ).fetchone()
        if p:
            if p['created_by']:
                user_ids.add(int(p['created_by']))
            if include_advisor:
                advisor_name = (p['advisor_name'] or '').strip()
                if advisor_name:
                    for tid in resolve_teacher_user_ids(conn, advisor_name):
                        user_ids.add(int(tid))
    except Exception:
        p = None

    try:
        rows = conn.execute(
            '''
            SELECT DISTINCT u.id AS user_id
            FROM project_members pm
            JOIN users u ON TRIM(u.identity_number) = TRIM(pm.student_id)
            WHERE pm.project_id = ?
              AND COALESCE(TRIM(pm.student_id), '') != ''
            ''',
            (project_id,)
        ).fetchall()
        for r in rows:
            if r['user_id']:
                user_ids.add(int(r['user_id']))
    except Exception:
        pass

    try:
        rows = conn.execute(
            '''
            SELECT DISTINCT u.id AS user_id
            FROM project_members pm
            JOIN users u ON TRIM(u.real_name) = TRIM(pm.name)
            WHERE pm.project_id = ?
              AND COALESCE(TRIM(pm.student_id), '') = ''
              AND COALESCE(TRIM(u.identity_number), '') = ''
              AND COALESCE(TRIM(pm.name), '') != ''
            ''',
            (project_id,)
        ).fetchall()
        for r in rows:
            if r['user_id']:
                user_ids.add(int(r['user_id']))
    except Exception:
        pass

    try:
        rows = conn.execute(
            '''
            SELECT DISTINCT u.id AS user_id
            FROM project_members pm
            JOIN users u ON TRIM(u.phone) = TRIM(pm.contact)
            WHERE pm.project_id = ?
              AND COALESCE(TRIM(pm.contact), '') != ''
              AND COALESCE(TRIM(u.phone), '') != ''
            ''',
            (project_id,)
        ).fetchall()
        for r in rows:
            if r['user_id']:
                user_ids.add(int(r['user_id']))
    except Exception:
        pass

    try:
        rows = conn.execute(
            '''
            SELECT DISTINCT u.id AS user_id
            FROM project_members pm
            JOIN users u ON TRIM(u.real_name) = TRIM(pm.name)
            WHERE pm.project_id = ?
              AND COALESCE(TRIM(pm.student_id), '') = ''
              AND COALESCE(TRIM(pm.name), '') != ''
              AND COALESCE(TRIM(pm.college), '') != ''
              AND COALESCE(TRIM(u.college), '') = COALESCE(TRIM(pm.college), '')
            ''',
            (project_id,)
        ).fetchall()
        for r in rows:
            if r['user_id']:
                user_ids.add(int(r['user_id']))
    except Exception:
        pass

    if exclude_user_id is not None:
        try:
            user_ids.discard(int(exclude_user_id))
        except Exception:
            pass

    for uid in user_ids:
        create_notification(conn, uid, title, content, 'project', meta={'route': f'/project/{int(project_id)}', 'project_id': int(project_id)})


@projects_bp.route('/post-event/upload', methods=['POST'])
@login_required
@role_required([ROLES['STUDENT']])
def upload_post_event_certificate():
    user_id = session.get('user_id')
    f = request.files.get('file')
    if not f:
        return fail('未选择文件', 400)

    filename = secure_filename(f.filename or '')
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ['.jpg', '.jpeg', '.png', '.pdf']:
        return fail('仅支持上传 jpg/png/pdf 文件', 400)

    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'post_event')
    try:
        os.makedirs(upload_dir, exist_ok=True)
    except Exception:
        pass

    ts = datetime.now().strftime('%Y%m%d%H%M%S%f')
    token = str(uuid.uuid4())[:8]
    save_name = f'post_event_{user_id}_{ts}_{token}{ext}'
    abs_path = os.path.join(upload_dir, save_name)
    try:
        f.save(abs_path)
    except Exception as e:
        return fail(str(e), 500)

    return success(data={'url': f'/static/uploads/post_event/{save_name}'})


@projects_bp.route('/post-event/my-projects', methods=['GET'])
@login_required
@role_required([ROLES['STUDENT']])
def list_my_post_event_projects():
    user_id = session.get('user_id')
    conn = get_db_connection()
    rows = conn.execute(
        '''
        SELECT p.id, p.title, p.status, p.year,
               r.status AS report_status,
               r.reject_reason AS report_reject_reason,
               r.submitted_at AS report_submitted_at
        FROM projects p
        LEFT JOIN post_event_reports r ON r.project_id = p.id
        WHERE p.created_by = ?
          AND p.status IN ('rated', 'finished', 'finished_national_award')
        ORDER BY p.id DESC
        ''',
        (user_id,)
    ).fetchall()
    return success(data=[dict(r) for r in rows])


@projects_bp.route('/post-event/report/<int:project_id>', methods=['GET'])
@login_required
@role_required([ROLES['STUDENT']])
def get_post_event_report(project_id):
    if project_id in GHOST_PROJECT_IDS:
        return fail('项目不存在', 404)
    user_id = session.get('user_id')
    conn = get_db_connection()
    p = conn.execute('SELECT id, title, created_by FROM projects WHERE id = ?', (project_id,)).fetchone()
    if not p:
        return fail('项目不存在', 404)
    if int(p['created_by']) != int(user_id):
        return fail('仅项目负责人可填报', 403)

    row = conn.execute('SELECT * FROM post_event_reports WHERE project_id = ?', (project_id,)).fetchone()
    return success(data=dict(row) if row else None)


@projects_bp.route('/post-event/report/<int:project_id>', methods=['POST'])
@login_required
@role_required([ROLES['STUDENT']])
def submit_post_event_report(project_id):
    if project_id in GHOST_PROJECT_IDS:
        return fail('项目不存在', 404)
    user_id = session.get('user_id')
    data = request.json or {}

    conn = get_db_connection()
    p = conn.execute('SELECT id, title, created_by, college FROM projects WHERE id = ?', (project_id,)).fetchone()
    if not p:
        return fail('项目不存在', 404)
    if int(p['created_by']) != int(user_id):
        return fail('仅项目负责人可填报', 403)

    prov_level = normalize_award_level(data.get('provincial_award_level'))
    nat_level = normalize_award_level(data.get('national_award_level'))
    prov_level = prov_level if prov_level else 'none'
    nat_level = nat_level if nat_level else 'none'

    if (prov_level in ['', 'none']) and (nat_level in ['', 'none']):
        return fail('至少填写省赛或国赛的一项获奖信息', 400)

    prov_cert_no = (data.get('provincial_certificate_no') or '').strip()
    nat_cert_no = (data.get('national_certificate_no') or '').strip()
    prov_file = (data.get('provincial_certificate_file') or '').strip()
    nat_file = (data.get('national_certificate_file') or '').strip()
    prov_adv = 0

    existing = conn.execute('SELECT * FROM post_event_reports WHERE project_id = ?', (project_id,)).fetchone()
    if existing and str(existing['status'] or '').strip() in ['pending', 'approved']:
        return fail('该项目已有待审核/已生效记录，不能重复提交', 400)

    try:
        if existing:
            conn.execute(
                '''
                UPDATE post_event_reports
                SET submitted_by = ?,
                    submitted_at = CURRENT_TIMESTAMP,
                    status = 'pending',
                    reject_reason = NULL,
                    reviewed_by = NULL,
                    reviewed_at = NULL,
                    provincial_award_level = ?,
                    provincial_certificate_no = ?,
                    provincial_certificate_file = ?,
                    provincial_advance_national = ?,
                    national_award_level = ?,
                    national_certificate_no = ?,
                    national_certificate_file = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE project_id = ?
                ''',
                (
                    user_id,
                    prov_level,
                    prov_cert_no,
                    prov_file,
                    prov_adv,
                    nat_level,
                    nat_cert_no,
                    nat_file,
                    project_id
                )
            )
        else:
            conn.execute(
                '''
                INSERT INTO post_event_reports
                (project_id, submitted_by, submitted_at, status,
                 provincial_award_level, provincial_certificate_no, provincial_certificate_file, provincial_advance_national,
                 national_award_level, national_certificate_no, national_certificate_file, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP, 'pending', ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''',
                (
                    project_id,
                    user_id,
                    prov_level,
                    prov_cert_no,
                    prov_file,
                    prov_adv,
                    nat_level,
                    nat_cert_no,
                    nat_file
                )
            )

        try:
            u = conn.execute('SELECT real_name, username FROM users WHERE id = ?', (user_id,)).fetchone()
            submitter = sanitize_public_text((u['real_name'] if u else '') or (u['username'] if u else '') or '')
            create_role_notifications(
                conn,
                ROLES['COLLEGE_APPROVER'],
                '获奖信息待审核',
                f'项目《{p["title"]}》赛后信息填报已提交（填报人：{submitter}），请审核。',
                college=p['college'],
                exclude_user_id=None,
                meta={'route': f'/award-audit', 'project_id': int(project_id)}
            )
            create_role_notifications(
                conn,
                ROLES['SCHOOL_APPROVER'],
                '获奖信息待审核',
                f'项目《{p["title"]}》赛后信息填报已提交（填报人：{submitter}），请审核。',
                exclude_user_id=None,
                meta={'route': f'/award-audit', 'project_id': int(project_id)}
            )
        except Exception:
            pass

        conn.commit()
        return success(message='已提交审核')
    except Exception as e:
        conn.rollback()
        return fail(str(e), 500)


@projects_bp.route('/post-event/admin/pending', methods=['GET'])
@login_required
@role_required([ROLES['COLLEGE_APPROVER'], ROLES['SCHOOL_APPROVER'], ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN']])
def list_pending_post_event_reports():
    role = session.get('role')
    college = session.get('college')
    conn = get_db_connection()
    if role == ROLES['COLLEGE_APPROVER'] and college:
        rows = conn.execute(
            '''
            SELECT r.id, r.project_id, r.submitted_at, u.real_name AS submitter_name, p.title AS project_title
            FROM post_event_reports r
            JOIN projects p ON p.id = r.project_id
            JOIN users u ON u.id = r.submitted_by
            WHERE r.status = 'pending' AND p.college = ?
            ORDER BY r.submitted_at DESC
            ''',
            (college,)
        ).fetchall()
    else:
        rows = conn.execute(
            '''
            SELECT r.id, r.project_id, r.submitted_at, u.real_name AS submitter_name, p.title AS project_title
            FROM post_event_reports r
            JOIN projects p ON p.id = r.project_id
            JOIN users u ON u.id = r.submitted_by
            WHERE r.status = 'pending'
            ORDER BY r.submitted_at DESC
            '''
        ).fetchall()
    return success(data=[dict(r) for r in rows])


@projects_bp.route('/post-event/admin/report/<int:report_id>', methods=['GET'])
@login_required
@role_required([ROLES['COLLEGE_APPROVER'], ROLES['SCHOOL_APPROVER'], ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN']])
def get_post_event_report_for_admin(report_id):
    conn = get_db_connection()
    row = conn.execute(
        '''
        SELECT r.*, p.title AS project_title, p.college AS project_college, u.real_name AS submitter_name
        FROM post_event_reports r
        JOIN projects p ON p.id = r.project_id
        JOIN users u ON u.id = r.submitted_by
        WHERE r.id = ?
        ''',
        (report_id,)
    ).fetchone()
    if not row:
        return fail('记录不存在', 404)

    role = session.get('role')
    college = session.get('college')
    if role == ROLES['COLLEGE_APPROVER'] and college and str(row['project_college'] or '').strip() != str(college or '').strip():
        return fail('无权限', 403)

    return success(data=dict(row))


@projects_bp.route('/post-event/admin/review/<int:report_id>', methods=['POST'])
@login_required
@role_required([ROLES['COLLEGE_APPROVER'], ROLES['SCHOOL_APPROVER'], ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN']])
def review_post_event_report(report_id):
    user_id = session.get('user_id')
    role = session.get('role')
    college = session.get('college')
    data = request.json or {}
    action = (data.get('action') or '').strip()
    reject_reason = sanitize_public_text(data.get('reject_reason') or '')
    rec_req = 1 if data.get('recommended_to_national') else 0

    if action not in ['approve', 'reject']:
        return fail('参数错误', 400)
    if action == 'reject' and not reject_reason:
        return fail('驳回理由为必填项', 400)

    conn = get_db_connection()
    row = conn.execute(
        '''
        SELECT r.*, p.title AS project_title, p.college AS project_college
        FROM post_event_reports r
        JOIN projects p ON p.id = r.project_id
        WHERE r.id = ?
        ''',
        (report_id,)
    ).fetchone()
    if not row:
        return fail('记录不存在', 404)
    if str(row['status'] or '').strip() != 'pending':
        return fail('该记录不在待审核状态', 400)
    if role == ROLES['COLLEGE_APPROVER'] and college and str(row['project_college'] or '').strip() != str(college or '').strip():
        return fail('无权限', 403)

    project_id = int(row['project_id'])
    p_title = str(row['project_title'] or '').strip() or f'项目#{project_id}'
    prov_level = normalize_award_level(row['provincial_award_level']) or 'none'
    nat_level = normalize_award_level(row['national_award_level']) or 'none'
    eligible_rec = prov_level in ['special', 'first', 'gold']
    rec_effective = 1 if str(row['provincial_advance_national'] or '').strip() in ['1', 'true', 'True'] else 0
    if role in [ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN']]:
        if rec_req and not eligible_rec:
            return fail('当前获奖等级不支持推荐至国赛', 400)
        rec_effective = 1 if rec_req else 0
    else:
        if rec_req:
            return fail('无权限操作“是否推荐至国赛”', 403)

    try:
        if action == 'approve':
            conn.execute(
                '''
                UPDATE post_event_reports
                SET status = 'approved',
                    reject_reason = NULL,
                    reviewed_by = ?,
                    reviewed_at = CURRENT_TIMESTAMP,
                    provincial_advance_national = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                ''',
                (user_id, rec_effective, report_id)
            )
            conn.execute(
                '''
                UPDATE projects
                SET provincial_award_level = ?,
                    provincial_certificate_no = ?,
                    provincial_certificate_file = ?,
                    national_award_level = ?,
                    national_certificate_no = ?,
                    national_certificate_file = ?,
                    provincial_advance_national = ?,
                    provincial_status = CASE
                        WHEN COALESCE(provincial_status, '') IN ('已晋级', '未晋级') THEN provincial_status
                        WHEN ? != 'none' THEN '已获奖'
                        ELSE COALESCE(provincial_status, '')
                    END,
                    national_status = CASE WHEN ? != 'none' THEN '已获奖' ELSE COALESCE(national_status, '') END
                WHERE id = ?
                ''',
                (
                    prov_level,
                    row['provincial_certificate_no'] or '',
                    row['provincial_certificate_file'] or '',
                    nat_level,
                    row['national_certificate_no'] or '',
                    row['national_certificate_file'] or '',
                    rec_effective,
                    prov_level,
                    nat_level,
                    project_id
                )
            )
            if prov_level and prov_level != 'none':
                node_status = '已晋级' if rec_effective else '未晋级'
                try:
                    conn.execute(
                        '''
                        INSERT OR REPLACE INTO project_node_status
                        (project_id, node_name, current_status, comment, award_level, updated_by, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        ''',
                        (project_id, '省赛', node_status, '', award_level_code_to_label(prov_level), user_id)
                    )
                except Exception:
                    pass
            if rec_effective:
                try:
                    conn.execute(
                        'UPDATE projects SET current_level = ?, review_stage = ? WHERE id = ?',
                        ('national', 'national', project_id)
                    )
                except Exception:
                    pass
                try:
                    conn.execute(
                        '''
                        INSERT OR REPLACE INTO project_node_status
                        (project_id, node_name, current_status, comment, award_level, updated_by, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        ''',
                        (project_id, '国赛', '待评审', '', '', user_id)
                    )
                except Exception:
                    pass
                try:
                    p = conn.execute('SELECT title, created_by, advisor_name FROM projects WHERE id = ?', (project_id,)).fetchone()
                    title_txt = str((p['title'] if p else '') or '').strip() or p_title
                    if p and p['created_by']:
                        create_notification(
                            conn,
                            p['created_by'],
                            '已推荐至国赛',
                            f'项目《{title_txt}》已推荐至国赛，国赛阶段已解锁。',
                            'project',
                            meta={'route': f'/project/{int(project_id)}', 'project_id': int(project_id)}
                        )
                    adv = (p['advisor_name'] if p else '') or ''
                    for tid in resolve_teacher_user_ids(conn, adv):
                        create_notification(
                            conn,
                            tid,
                            '已推荐至国赛',
                            f'项目《{title_txt}》已推荐至国赛，国赛阶段已解锁。',
                            'project',
                            meta={'route': f'/project/{int(project_id)}', 'project_id': int(project_id)}
                        )
                except Exception:
                    pass
            else:
                try:
                    conn.execute(
                        '''
                        UPDATE project_node_status
                        SET current_status = '', comment = '', award_level = '', updated_by = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE project_id = ? AND node_name = ?
                        ''',
                        (user_id, project_id, '国赛')
                    )
                except Exception:
                    pass
            try:
                create_project_related_notifications(
                    conn,
                    project_id,
                    '获奖信息审核通过',
                    f'项目《{p_title}》赛后信息填报审核通过，已生效并同步到项目详情。',
                    exclude_user_id=user_id,
                    include_advisor=False
                )
            except Exception:
                pass
        else:
            conn.execute(
                '''
                UPDATE post_event_reports
                SET status = 'rejected',
                    reject_reason = ?,
                    reviewed_by = ?,
                    reviewed_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                ''',
                (reject_reason, user_id, report_id)
            )
            try:
                create_project_related_notifications(
                    conn,
                    project_id,
                    '获奖信息审核驳回',
                    f'项目《{p_title}》赛后信息填报被驳回，驳回理由：{reject_reason}',
                    exclude_user_id=user_id,
                    include_advisor=False
                )
            except Exception:
                pass

        conn.commit()
        return success(message='已处理')
    except Exception as e:
        conn.rollback()
        return fail(str(e), 500)

def append_experience_audit_log(info, role, action, opinion, reviewer_id):
    payload = info if isinstance(info, dict) else {}
    logs = payload.get('experience_audit_logs')
    if not isinstance(logs, list):
        logs = []
    logs.append({
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'role': str(role or ''),
        'action': str(action or ''),
        'opinion': sanitize_public_text(opinion),
        'reviewer_id': int(reviewer_id or 0)
    })
    payload['experience_audit_logs'] = logs
    return payload

def log_action(conn, user_id, action, details, ip_address):
    try:
        conn.execute('INSERT INTO system_logs (user_id, action, details, ip_address) VALUES (?, ?, ?, ?)',
                    (user_id, action, details, ip_address))
    except Exception as e:
        print(f"LOG ERROR: {e}")

def _extract_collaborators_from_extra_info(extra_info):
    if not isinstance(extra_info, dict):
        return []
    out = []
    for k in ['collaborators_team', 'collaborators_individual']:
        rows = extra_info.get(k)
        if not isinstance(rows, list):
            continue
        for r in rows:
            if not isinstance(r, dict):
                continue
            name = str(r.get('姓名') or r.get('name') or '').strip()
            student_id = str(r.get('学号') or r.get('student_id') or '').strip()
            college = str(r.get('学院') or r.get('college') or '').strip()
            major = str(r.get('专业') or r.get('major') or '').strip()
            role = str(r.get('承担工作') or r.get('role') or '').strip()
            if not name and not student_id:
                continue
            out.append({
                'name': name,
                'student_id': student_id,
                'college': college,
                'major': major,
                'grade': '',
                'role': role,
                'contact': ''
            })
    return out

def _merge_member_payloads(members, extra_info, leader_sid='', leader_name=''):
    leader_sid = str(leader_sid or '').strip()
    leader_name = str(leader_name or '').strip()

    base = []
    if isinstance(members, list):
        for m in members:
            if isinstance(m, dict):
                base.append(m)
    base.extend(_extract_collaborators_from_extra_info(extra_info))

    seen = set()
    out = []
    for m in base:
        if not isinstance(m, dict):
            continue
        name = str(m.get('name') or '').strip()
        student_id = str(m.get('student_id') or '').strip()
        college = str(m.get('college') or '').strip()
        major = str(m.get('major') or '').strip()
        grade = str(m.get('grade') or '').strip()
        role = str(m.get('role') or '').strip()
        contact = str(m.get('contact') or '').strip()
        if leader_sid and student_id and student_id == leader_sid:
            continue
        if leader_name and name and name == leader_name:
            continue
        if student_id:
            key = ('sid', student_id)
        elif name and college:
            key = ('name_college', name, college)
        elif name:
            key = ('name', name)
        else:
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append({
            'name': name,
            'student_id': student_id,
            'college': college,
            'major': major,
            'grade': grade,
            'role': role,
            'contact': contact
        })
    return out

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
        u = conn.execute('SELECT identity_number, real_name, username FROM users WHERE id = ?', (user_id,)).fetchone()
        sid = (u['identity_number'] if u else '') or ''
        rn = (u['real_name'] if u else '') or ''
        un = (u['username'] if u else '') or ''
        cands = []
        for v in [sid, un]:
            vv = str(v or '').strip()
            if vv and vv not in cands:
                cands.append(vv)
        if cands:
            placeholders = ','.join(['?'] * len(cands))
            like_part = ' OR '.join(['p.extra_info LIKE ?'] * len(cands))
            query += f" AND (p.created_by = ? OR p.id IN (SELECT project_id FROM project_members WHERE TRIM(student_id) IN ({placeholders})) OR p.id IN (SELECT project_id FROM project_members WHERE name = ? AND COALESCE(TRIM(student_id),'') = '') OR ({like_part}))"
            params.extend([user_id] + cands + [rn] + [f"%{v}%" for v in cands])
        else:
            query += " AND (p.created_by = ? OR p.id IN (SELECT project_id FROM project_members WHERE name = ? AND COALESCE(TRIM(student_id),'') = ''))"
            params.extend([user_id, rn])
    elif role == ROLES['COLLEGE_APPROVER']:
        # 学院审批者可以看到本学院的所有项目，确保流程透明
        user_info = conn.execute('SELECT college FROM users WHERE id = ?', (user_id,)).fetchone()
        if user_info and user_info['college']:
            query += " AND p.college = ?"
            params.append(user_info['college'])
    elif role == ROLES['TEACHER']:
        # 指导老师仅查看与自己相关的项目（advisor_name 绑定）
        teacher = conn.execute('SELECT real_name FROM users WHERE id = ?', (user_id,)).fetchone()
        tname = (teacher['real_name'] if teacher else '') or ''
        if tname:
            query += " AND p.advisor_name = ?"
            params.append(tname)
        else:
            query += " AND 0=1"
    elif role == ROLES['JUDGE']:
        # 评委仅看分配给自己的项目
        query += " AND p.id IN (SELECT project_id FROM review_tasks WHERE judge_id = ?)"
        params.append(user_id)
    elif role in [ROLES['SCHOOL_APPROVER'], ROLES['PROJECT_ADMIN'], ROLES['SYSTEM_ADMIN']]:
        # 校级管理员看全校
        pass
        
    if GHOST_PROJECT_IDS:
        query += f" AND p.id NOT IN ({','.join(map(str, GHOST_PROJECT_IDS))})"
    
    query += " ORDER BY p.created_at DESC"
    
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
        if role == ROLES['COLLEGE_APPROVER'] and p.get('project_type') == 'innovation':
            st = str(p.get('status') or '').strip()
            rej_lv = str((p.get('extra_info') or {}).get('rejection_level') or '').strip()
            if st == 'pending_teacher':
                continue
            if st == 'rejected' and rej_lv in ['导师', '指导教师']:
                continue
            
        p['resolved_template_name'] = resolve_template_name(p)
        results.append(p)

    dachiang_ids = [p['id'] for p in results if p.get('resolved_template_name') == '大挑']
    if dachiang_ids:
        placeholders = ','.join(['?'] * len(dachiang_ids))
        task_rows = conn.execute(
            f'''
            SELECT project_id, judge_id, review_level, status, score, is_recommended
            FROM review_tasks
            WHERE project_id IN ({placeholders}) AND review_level IN ('college', 'school')
            ''',
            dachiang_ids
        ).fetchall()
        task_map = {}
        for t in task_rows:
            pid = t['project_id']
            lv = t['review_level']
            task_map.setdefault(pid, {}).setdefault(lv, []).append(dict(t))
            
        for p in results:
            if p.get('resolved_template_name') != '大挑':
                continue
            pid = p.get('id')
            per = task_map.get(pid, {})
            
            # 为前端展示评分详情提供数据
            p['review_details'] = per.get('college') or []
            p['school_review_details'] = per.get('school') or []
            
            def calc(level):
                tasks = per.get(level) or []
                if not tasks:
                    return None
                if not all(r['status'] == 'completed' for r in tasks):
                    return None
                rc = sum(1 for r in tasks if int(r['is_recommended'] or 0) == 1)
                rec = 1 if rc > (len(tasks) / 2) else 0
                return 'approved' if rec else 'rejected'
            
            cr = calc('college')
            sr = calc('school')

            st = str(p.get('status') or '').strip()
            # 大挑改为“手动确认推荐”机制：
            # - 评委打分完成后不自动写入/推断推荐结果与阶段
            # - 仅在学院/学校管理员确认推荐后，才由项目表字段体现推进
            if st not in ['pending_college_recommendation', 'pending_school_recommendation']:
                if cr and not p.get('college_review_result'):
                    p['college_review_result'] = cr
                if sr and not p.get('school_review_result'):
                    p['school_review_result'] = sr

            if int(p.get('provincial_advance_national') or 0) == 1:
                p['current_level'] = 'national'
                p['review_stage'] = 'national'
            elif st not in ['pending_college_recommendation', 'pending_school_recommendation']:
                if sr == 'approved':
                    p['current_level'] = 'provincial'
                    p['review_stage'] = 'provincial'
                elif cr == 'approved':
                    p['current_level'] = 'school'
                    p['review_stage'] = 'school'
    
    return success(data=results)

@projects_bp.route('/projects/advisor-pending', methods=['GET'])
@login_required
@role_required([ROLES['TEACHER']])
def get_advisor_pending_projects():
    user_id = session.get('user_id')
    conn = get_db_connection()
    teacher = conn.execute('SELECT real_name FROM users WHERE id = ?', (user_id,)).fetchone()
    if not teacher or not teacher['real_name']:
        return success(data=[])
        
    query = '''
        SELECT p.*, c.title as competition_title, c.template_type as competition_template_type 
        FROM projects p
        LEFT JOIN competitions c ON p.competition_id = c.id
        WHERE p.status IN (?, ?) AND p.advisor_name = ?
    '''
    params = ['pending_advisor_review', 'pending_teacher', teacher['real_name']]
    
    if GHOST_PROJECT_IDS:
        query += f" AND p.id NOT IN ({','.join(map(str, GHOST_PROJECT_IDS))})"
    query += " ORDER BY p.created_at DESC"
    
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

@projects_bp.route('/projects/<int:project_id>/advisor_review', methods=['POST'])
@login_required
@role_required([ROLES['TEACHER']])
def advisor_review_project(project_id):
    """
    指导教师初审项目
    """
    user_id = session.get('user_id')
    data = request.json
    status = data.get('status')  # 'pass' or 'reject'
    opinion = data.get('opinion', '')
    
    if not opinion or not opinion.strip():
        return fail('审批意见为必填项', 400)
    
    if status not in ['pass', 'reject']:
        return fail('审批状态无效', 400)
        
    conn = get_db_connection()
    try:
        user = conn.execute('SELECT real_name FROM users WHERE id = ?', (user_id,)).fetchone()
        project = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
        
        if not project:
            return fail('项目不存在', 404)
            
        # 权限校验：仅第一指导教师可审
        bound = str(project.get('advisor_name') or '').strip()
        reviewer = str(user.get('real_name') or '').strip()
        if bound != reviewer:
            ok = False
            if not bound:
                try:
                    info = json.loads(project['extra_info']) if project.get('extra_info') else {}
                except Exception:
                    info = {}
                try:
                    adv = info.get('advisors') if isinstance(info, dict) else None
                    if isinstance(adv, list):
                        ok = any(isinstance(a, dict) and str(a.get('name') or '').strip() == reviewer for a in adv)
                except Exception:
                    ok = False
            if not ok:
                return fail('您不是该项目的第一指导教师，无权初审', 403)
            conn.execute('UPDATE projects SET advisor_name = ? WHERE id = ?', (reviewer, project_id))
            
        if project['status'] != 'pending_advisor_review':
            return fail('项目当前状态不可进行指导教师初审', 400)
            
        new_status = 'college_review' if status == 'pass' else 'to_modify'
        
        conn.execute('''
            UPDATE projects 
            SET status = ?, advisor_review_opinion = ?, advisor_review_time = CURRENT_TIMESTAMP 
            WHERE id = ?
        ''', (new_status, opinion, project_id))
        
        # 同步更新过程节点状态（针对大挑等有显式过程节点的模板）
        template_name = resolve_template_name(project)
        if template_name == '大挑':
            node_status = '已通过' if status == 'pass' else '已驳回'
            conn.execute(
                'INSERT OR REPLACE INTO project_node_status (project_id, node_name, current_status, comment, updated_by, updated_at) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)',
                (project_id, '指导教师初审', node_status, opinion, user_id)
            )
            # 如果初审通过，自动初始化下一个节点：学院赛
            if status == 'pass':
                conn.execute(
                    'INSERT OR IGNORE INTO project_node_status (project_id, node_name, current_status, comment, updated_by, updated_at) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)',
                    (project_id, '学院赛', '待评审', '', user_id)
                )
        
        msg = f"您的项目《{project['title']}》指导教师初审已{'通过' if status == 'pass' else '驳回'}。理由：{opinion}"
        create_notification(conn, project['created_by'], '指导教师初审结果', msg, 'info')
        if status == 'pass':
            create_role_notifications(
                conn,
                ROLES['COLLEGE_APPROVER'],
                '待学院审核',
                f"项目《{project['title']}》已通过指导教师初审，请进行学院审核。",
                college=project['college'],
                exclude_user_id=user_id
            )
        
        log_action(conn, user_id, 'ADVISOR_REVIEW', f"Review {project['title']}: {status}. Opinion: {opinion}", request.remote_addr)
        conn.commit()
        return success(message='初审操作成功')
    except Exception as e:
        conn.rollback()
        return fail(str(e), 500)

@projects_bp.route('/projects/<int:project_id>/audit', methods=['PUT'])
@login_required
def audit_project(project_id):
    role = session.get('role')
    user_id = session.get('user_id')
    data = request.json or {}
    action = (data.get('action') or '').strip()
    feedback = (data.get('feedback') or '').strip()
    project_level = (data.get('project_level') or '').strip()
    final_grade = (data.get('final_grade') or '').strip()
    
    if action not in ['approve', 'reject']:
        return fail('参数错误', 400)
    if action == 'reject' and not feedback:
        return fail('驳回时审批意见为必填项', 400)
        
    conn = get_db_connection()
    project = conn.execute(
        '''
        SELECT p.*, c.template_type AS competition_template_type, c.title AS competition_title
        FROM projects p
        LEFT JOIN competitions c ON p.competition_id = c.id
        WHERE p.id = ?
        ''',
        (project_id,)
    ).fetchone()
    if not project:
        return fail('项目不存在', 404)
    project = dict(project)
        
    try:
        try:
            info = json.loads(project['extra_info']) if project['extra_info'] else {}
        except Exception:
            info = {}
            
        new_status = project['status']
        tpl = resolve_template_name(project)
        is_dachuang_innovation = (tpl == '大创创新训练')
        is_dachuang_entrepreneurship = (tpl in ['大创创业训练', '大创创业实践'])
        is_dachuang_training = is_dachuang_innovation or is_dachuang_entrepreneurship
        
        if role == ROLES['TEACHER']:
            if is_dachuang_training:
                # 大创项目统一流程：初审(pending_teacher) -> 中期(midterm_submitted) -> 结题(conclusion_submitted)
                allowed = ['pending_teacher', 'midterm_submitted', 'conclusion_submitted']
                if project['status'] not in allowed:
                    return fail(f'当前状态({project["status"]})无法进行指导老师审核', 400)
                
                user_row = conn.execute('SELECT real_name FROM users WHERE id = ?', (user_id,)).fetchone()
                teacher_name = (user_row['real_name'] if user_row else '') or ''
                
                # 权限校验：仅指定导师可审
                if is_dachuang_innovation:
                    bound = str(project.get('advisor_name') or '').strip()
                    if bound and bound != str(teacher_name).strip():
                        return fail('仅项目指定指导教师可审核', 403)
                else:
                    try:
                        adv = (info.get('advisors') or []) if isinstance(info, dict) else []
                        ok = any(isinstance(a, dict) and str(a.get('guidance_type') or '').strip() == '校内导师' and str(a.get('name') or '').strip() == str(teacher_name).strip() for a in adv)
                    except Exception:
                        ok = False
                    if not ok:
                        return fail('仅项目校内导师可审核', 403)
                
                # 状态流转
                if project['status'] == 'pending_teacher':
                    new_status = 'pending_college' if action == 'approve' else 'rejected'
                    # 自动绑定导师名
                    if is_dachuang_innovation and not str(project.get('advisor_name') or '').strip() and str(teacher_name).strip():
                        conn.execute('UPDATE projects SET advisor_name = ? WHERE id = ?', (str(teacher_name).strip(), project_id))
                elif project['status'] == 'midterm_submitted':
                    new_status = 'midterm_advisor_approved' if action == 'approve' else 'midterm_rejected'
                elif project['status'] == 'conclusion_submitted':
                    new_status = 'conclusion_advisor_approved' if action == 'approve' else 'conclusion_rejected'
            else:
                allowed = ['pending', 'pending_teacher', 'midterm_submitted', 'conclusion_submitted']
                if project['status'] not in allowed:
                    return fail(f'当前状态({project["status"]})无法进行指导老师审核', 400)
                if project['status'] == 'pending':
                    new_status = 'advisor_approved' if action == 'approve' else 'rejected'
                elif project['status'] == 'pending_teacher':
                    new_status = 'pending_college' if action == 'approve' else 'rejected'
                elif project['status'] == 'midterm_submitted':
                    new_status = 'midterm_advisor_approved' if action == 'approve' else 'midterm_rejected'
                elif project['status'] == 'conclusion_submitted':
                    new_status = 'conclusion_advisor_approved' if action == 'approve' else 'conclusion_rejected'
                
            if feedback or action == 'reject':
                info['advisor_feedback'] = feedback
            if action == 'reject':
                info['rejection_level'] = '导师'
                info['rejection_reason'] = feedback
                
            conn.execute('UPDATE projects SET status = ?, extra_info = ? WHERE id = ?', (new_status, json.dumps(info), project_id))
            
        elif role == ROLES['COLLEGE_APPROVER']:
            if is_dachuang_training:
                # 大创项目统一流程：初审(pending_college) -> 中期(midterm_advisor_approved) -> 结题(conclusion_advisor_approved)
                allowed = ['pending_college', 'midterm_advisor_approved', 'conclusion_advisor_approved']
                if project['status'] not in allowed:
                    return fail(f'当前状态({project["status"]})无法进行学院审核', 400)
                
                if project['status'] == 'pending_college':
                    if is_dachuang_innovation:
                        new_status = 'reviewing' if action == 'approve' else 'rejected'
                    else: # 创业类
                        if action == 'approve':
                            info['college_qualified'] = 1
                            info['college_qualified_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            new_status = 'pending_college' # 保持状态或进入评审
                        else:
                            new_status = 'rejected'
                elif project['status'] == 'midterm_advisor_approved':
                    new_status = 'midterm_college_approved' if action == 'approve' else 'midterm_rejected'
                elif project['status'] == 'conclusion_advisor_approved':
                    new_status = 'conclusion_college_approved' if action == 'approve' else 'conclusion_rejected'
            else:
                if project['project_type'] in ['entrepreneurship_training', 'entrepreneurship_practice'] and project['status'] == 'advisor_approved':
                    return fail('该项目跳过学院评审环节，由学校统一评审', 400)
                allowed = ['advisor_approved', 'midterm_advisor_approved', 'conclusion_advisor_approved']
                if project['status'] not in allowed:
                    return fail(f'当前状态({project["status"]})无法进行学院审批', 400)
                if project['status'] == 'advisor_approved':
                    new_status = 'college_approved' if action == 'approve' else 'rejected'
                elif project['status'] == 'midterm_advisor_approved':
                    new_status = 'midterm_college_approved' if action == 'approve' else 'midterm_rejected'
                elif project['status'] == 'conclusion_advisor_approved':
                    new_status = 'conclusion_college_approved' if action == 'approve' else 'conclusion_rejected'
                
            if feedback or action == 'reject':
                info['college_feedback'] = feedback
            if action == 'reject':
                info['rejection_level'] = '学院'
                info['rejection_reason'] = feedback
            
            if feedback:
                conn.execute('UPDATE projects SET status = ?, college_feedback = ?, extra_info = ? WHERE id = ?', (new_status, feedback, json.dumps(info), project_id))
            else:
                conn.execute('UPDATE projects SET status = ?, extra_info = ? WHERE id = ?', (new_status, json.dumps(info), project_id))
            
        elif role == ROLES['SCHOOL_APPROVER']:
            if is_dachuang_training:
                # 大创项目（创新、创业、实践）统一校级立项及过程流转逻辑
                # 申报阶段状态: college_recommended, approved, school_review, under_review, pending_college
                # 中期阶段状态: midterm_college_approved
                # 结题阶段状态: conclusion_college_approved
                allowed = [
                    'college_recommended', 'approved', 'school_review', 'under_review', 'pending_college',
                    'midterm_college_approved', 'conclusion_college_approved'
                ]
                if project['status'] not in allowed:
                    return fail(f'当前状态({project["status"]})无法进行学校复审', 400)
                
                if action == 'approve':
                    if project['status'] == 'midterm_college_approved':
                        new_status = 'midterm_approved'
                    elif project['status'] == 'conclusion_college_approved':
                        new_status = 'finished'
                    else:
                        new_status = 'rated'
                        # 立项通过后同步更新 current_level 和 review_stage 为学校级，确保解锁过程管理后续阶段
                        conn.execute(
                            'UPDATE projects SET current_level = ?, review_stage = ? WHERE id = ?',
                            ('school', 'school', project_id)
                        )
                else:
                    if project['status'] == 'midterm_college_approved':
                        new_status = 'midterm_rejected'
                    elif project['status'] == 'conclusion_college_approved':
                        new_status = 'conclusion_rejected'
                    else:
                        new_status = 'rejected'
            else:
                # 非大创类项目（如挑战杯等）的通用审批流
                allowed = ['college_approved', 'midterm_college_approved', 'conclusion_college_approved']
                if project['project_type'] in ['entrepreneurship_training', 'entrepreneurship_practice']:
                    allowed = list(set(allowed + ['advisor_approved']))
                if project['status'] not in allowed:
                    return fail(f'当前状态({project["status"]})无法进行学校审批', 400)
                if project['status'] == 'advisor_approved' and project['project_type'] in ['entrepreneurship_training', 'entrepreneurship_practice']:
                    new_status = 'school_approved' if action == 'approve' else 'rejected'
                elif project['status'] == 'college_approved':
                    new_status = 'school_approved' if action == 'approve' else 'rejected'
                elif project['status'] == 'midterm_college_approved':
                    new_status = 'midterm_approved' if action == 'approve' else 'midterm_rejected'
                elif project['status'] == 'conclusion_college_approved':
                    new_status = 'finished' if action == 'approve' else 'conclusion_rejected'
                
            if project_level:
                conn.execute('UPDATE projects SET level = ? WHERE id = ?', (project_level, project_id))
            if final_grade:
                info['final_grade'] = final_grade
                
            if feedback or action == 'reject':
                info['school_feedback'] = feedback
            if action == 'reject':
                info['rejection_level'] = '学校'
                info['rejection_reason'] = feedback
            
            if feedback:
                conn.execute('UPDATE projects SET status = ?, school_feedback = ?, extra_info = ? WHERE id = ?', (new_status, feedback, json.dumps(info), project_id))
            else:
                conn.execute('UPDATE projects SET status = ?, extra_info = ? WHERE id = ?', (new_status, json.dumps(info), project_id))
            if is_dachuang_training and new_status == 'rated':
                try:
                    auto_collect_legacy(conn, project_id, user_id)
                except Exception:
                    pass
            
        elif role in [ROLES['PROJECT_ADMIN'], ROLES['SYSTEM_ADMIN']]:
            conn.execute('UPDATE projects SET extra_info = ? WHERE id = ?', (json.dumps(info), project_id))
        else:
            return fail('无权限', 403)
            
        if action == 'approve':
            if role == ROLES['TEACHER']:
                if new_status in ['pending_college', 'midterm_advisor_approved', 'conclusion_advisor_approved']:
                    create_role_notifications(
                        conn,
                        ROLES['COLLEGE_APPROVER'],
                        '待学院审核',
                        f"项目《{project['title']}》已进入学院审核环节，请及时处理。",
                        college=project['college'],
                        exclude_user_id=user_id
                    )
                elif new_status == 'advisor_approved':
                    if project['project_type'] in ['entrepreneurship_training', 'entrepreneurship_practice']:
                        create_role_notifications(
                            conn,
                            ROLES['SCHOOL_APPROVER'],
                            '待学校审核',
                            f"项目《{project['title']}》已进入学校审核环节，请及时处理。",
                            exclude_user_id=user_id
                        )
                    else:
                        create_role_notifications(
                            conn,
                            ROLES['COLLEGE_APPROVER'],
                            '待学院审核',
                            f"项目《{project['title']}》已进入学院审核环节，请及时处理。",
                            college=project['college'],
                            exclude_user_id=user_id
                        )
            elif role == ROLES['COLLEGE_APPROVER']:
                if new_status in ['college_approved', 'midterm_college_approved', 'conclusion_college_approved']:
                    create_role_notifications(
                        conn,
                        ROLES['SCHOOL_APPROVER'],
                        '待学校审核',
                        f"项目《{project['title']}》已进入学校审核环节，请及时处理。",
                        exclude_user_id=user_id
                    )
                elif is_dachuang_training and new_status in ['reviewing', 'pending_college']:
                    create_role_notifications(
                        conn,
                        ROLES['COLLEGE_APPROVER'],
                        '待学院评审录入',
                        f"项目《{project['title']}》已通过学院资格审核，请继续完成学院评审录入与推荐。",
                        college=project['college'],
                        exclude_user_id=user_id
                    )

        try:
            create_project_related_notifications(
                conn,
                project_id,
                '项目审批结果',
                f'您的项目《{project["title"]}》审批结果：{new_status}',
                exclude_user_id=user_id,
                include_advisor=True
            )
        except Exception:
            create_notification(conn, project['created_by'], '项目审批结果', f'您的项目《{project["title"]}》审批结果：{new_status}', 'approval')
        log_action(conn, user_id, 'AUDIT', f'Audit project {project_id} -> {new_status}', request.remote_addr)
        conn.commit()
        return success(message='审批成功')
    except Exception as e:
        conn.rollback()
        return fail(str(e), 500)
    finally:
        conn.close()


@projects_bp.route('/projects/<int:project_id>/college-recommendation', methods=['PUT'])
@login_required
@role_required([ROLES['COLLEGE_APPROVER']])
def update_college_recommendation(project_id):
    if project_id in GHOST_PROJECT_IDS:
        return fail('项目不存在', 404)
    data = request.json or {}
    action = (data.get('action') or '').strip()
    defense_score = data.get('defense_score')
    recommend_rank = data.get('recommend_rank')
    is_key_support = 1 if str(data.get('is_key_support')) in ['1', 'true', 'True'] else 0
    feedback = sanitize_public_text(data.get('feedback'))
    user_id = session.get('user_id')
    
    if action not in ['qualification', 'defense', 'ranking']:
        return fail('参数错误', 400)
        
    conn = get_db_connection()
    project = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    if not project:
        return fail('项目不存在', 404)
        
    try:
        tpl = resolve_template_name(project)
        if tpl != '大创创新训练':
            return fail('仅支持创新训练项目', 400)
        if project['project_type'] != 'innovation':
            return fail('仅支持创新训练项目', 400)
            
        if project['year'] and int(project['year']) == 2026 and datetime.now() > DACHUANG_INNOVATION_COLLEGE_RECOMMEND_DEADLINE:
            return fail('已超过学院推荐截止时间（4月30日）', 400)
            
        try:
            info = json.loads(project['extra_info']) if project['extra_info'] else {}
        except Exception:
            info = {}
            
        if action == 'qualification':
            passed = str(data.get('passed')) in ['1', 'true', 'True']
            if not feedback:
                return fail('资格审核意见为必填项', 400)
            if passed:
                info['college_qualification_feedback'] = feedback
                info['college_qualified'] = 1
                info['college_qualified_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                conn.execute('UPDATE projects SET extra_info = ?, college_feedback = ? WHERE id = ?', (json.dumps(info, ensure_ascii=False), feedback, project_id))
            else:
                info['rejection_level'] = '学院'
                info['rejection_reason'] = feedback
                info['college_qualification_feedback'] = feedback
                conn.execute('UPDATE projects SET status = ?, extra_info = ?, college_feedback = ? WHERE id = ?', ('rejected', json.dumps(info, ensure_ascii=False), feedback, project_id))
            conn.commit()
            return success(message='资格审核已更新')
            
        if action == 'defense':
            if defense_score is None:
                return fail('defense_score 必填', 400)
            try:
                ds = float(defense_score)
            except Exception:
                return fail('defense_score 格式错误', 400)
            info['college_defense_scored_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if feedback:
                info['college_defense_feedback'] = feedback
            conn.execute(
                'UPDATE projects SET college_defense_score = ?, extra_info = ? WHERE id = ?',
                (ds, json.dumps(info, ensure_ascii=False), project_id)
            )
            conn.commit()
            return success(message='答辩成绩已录入')
            
        if recommend_rank is None:
            return fail('recommend_rank 必填', 400)
        try:
            rk = int(recommend_rank)
        except Exception:
            return fail('recommend_rank 格式错误', 400)
        if rk <= 0:
            return fail('recommend_rank 必须大于0', 400)
            
        if is_key_support == 1:
            if rk != 1:
                return fail('重点支持项目仅允许学院排序第1选择', 400)
            attachments = (info.get('attachments') or {}) if isinstance(info.get('attachments'), dict) else {}
            if not str(attachments.get('stage_achievement') or '').strip():
                return fail('重点支持项目必须上传已有阶段性成果', 400)
            exists = conn.execute(
                '''
                SELECT 1 FROM projects
                WHERE competition_id = ? AND college = ? AND project_type = 'innovation'
                  AND is_key_support = 1 AND id != ? AND status != 'rejected'
                ''',
                (project['competition_id'], project['college'], project_id)
            ).fetchone()
            if exists:
                return fail('本学院已存在重点支持项目（限1项）', 400)
                
        info['college_recommend_rank'] = rk
        info['is_key_support'] = is_key_support
        info['college_recommend_submitted_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if feedback:
            info['college_ranking_feedback'] = feedback

        cur_status = str(project.get('status') or '').strip()
        if cur_status not in ['reviewing', 'college_recommended']:
            return fail(f'当前状态({cur_status})无法提交学院排序与推荐', 400)

        conn.execute(
            'UPDATE projects SET status = ?, college_recommend_rank = ?, is_key_support = ?, extra_info = ? WHERE id = ?',
            ('college_recommended', rk, is_key_support, json.dumps(info, ensure_ascii=False), project_id)
        )
        create_role_notifications(
            conn,
            ROLES['SCHOOL_APPROVER'],
            '待学校审核',
            f"项目《{project['title']}》已完成学院排序与推荐，请进行学校审核。"
        )
        conn.commit()
        return success(message='学院排序与推荐已提交')
    except Exception as e:
        conn.rollback()
        return fail(str(e), 500)
    finally:
        conn.close()

@projects_bp.route('/projects/<int:project_id>', methods=['DELETE'])
@login_required
@role_required([ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN']])
def delete_project(project_id):
    """
    删除项目及其关联的所有数据（级联删除）
    """
    if project_id in GHOST_PROJECT_IDS:
        return fail('项目不存在', 404)
    
    conn = get_db_connection()
    try:
        project = conn.execute('SELECT id, title FROM projects WHERE id = ?', (project_id,)).fetchone()
        if not project:
            return fail('项目不存在', 404)
            
        # SQLite 已开启 foreign_keys=ON，会通过 ON DELETE CASCADE 自动清理：
        # project_members, innovation_projects, entrepreneurship_projects, 
        # project_reviews, review_tasks, project_files, project_upgrade_requests, 
        # project_awards, project_node_status
        
        conn.execute('DELETE FROM projects WHERE id = ?', (project_id,))
        
        # 额外清理经验库（如果存在，且未设级联）
        conn.execute('DELETE FROM project_legacy WHERE original_project_id = ?', (project_id,))
        
        log_action(conn, session.get('user_id'), 'DELETE_PROJECT', f'Deleted project: {project["title"]} (ID: {project_id})', request.remote_addr)
        conn.commit()
        return success(message='项目删除成功')
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Error deleting project {project_id}: {str(e)}")
        return fail(f'删除失败: {str(e)}', 500)

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
    is_draft = bool(data.get('is_draft'))
    
    if data.get('id') and str(data.get('id')).isdigit() and int(data.get('id')) > 0:
         return fail('项目ID已存在，请刷新页面后重试', 400)

    conn = get_db_connection()
    try:
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        sid0 = str((user['identity_number'] if user else '') or '').strip()
        rn0 = str((user['real_name'] if user else '') or '').strip()
        un0 = str((user['username'] if user else '') or '').strip()
        
        # 校验：项目名称不能重复 (优化建议)
        title = str(data.get('title') or '').strip()
        if not title:
            return fail('项目名称不能为空', 400)
        exist = conn.execute('SELECT id FROM projects WHERE title = ?', (title,)).fetchone()
        if exist:
            return fail('项目名称已存在', 400)
            
        linked_project_id = data.get('linked_project_id')
        if linked_project_id is not None and linked_project_id != '':
            try:
                linked_project_id = int(linked_project_id)
            except Exception:
                return fail('关联大创项目ID无效', 400)
            linked = conn.execute(
                'SELECT id, created_by FROM projects WHERE id = ? AND template_type = ?',
                (linked_project_id, 'training')
            ).fetchone()
            if not linked:
                return fail('关联大创项目不存在或无权限', 400)
            if int(linked['created_by']) != int(user_id):
                ok = None
                cands = []
                for v in [sid0, un0]:
                    vv = str(v or '').strip()
                    if vv and vv not in cands:
                        cands.append(vv)
                if cands:
                    placeholders = ','.join(['?'] * len(cands))
                    ok = conn.execute(
                        f'SELECT 1 FROM project_members WHERE project_id = ? AND TRIM(student_id) IN ({placeholders}) LIMIT 1',
                        [linked_project_id] + cands
                    ).fetchone()
                if not ok:
                    ok = conn.execute(
                        "SELECT 1 FROM project_members WHERE project_id = ? AND name = ? AND COALESCE(TRIM(student_id),'') = '' LIMIT 1",
                        (linked_project_id, rn0)
                    ).fetchone()
                if not ok:
                    return fail('关联大创项目不存在或无权限', 400)
            data['linked_project_id'] = linked_project_id
        else:
            data['linked_project_id'] = None

        extra_info = data.get('extra_info', {})
        p_type = data.get('project_type')
        t_type = data.get('template_type', 'default')
        raw_members = data.get('members', []) or []
        def _is_leader_member(m):
            mm = m if isinstance(m, dict) else {}
            role = str(mm.get('role') or '').strip()
            if role in ['leader', '负责人']:
                return True
            try:
                if int(mm.get('is_leader') or 0) == 1:
                    return True
            except Exception:
                pass
            sidm = str(mm.get('student_id') or '').strip()
            if sid0 and sidm and sidm == sid0:
                return True
            return False
        members = [m for m in raw_members if not _is_leader_member(m)]
        leader_sid = sid0 or un0
        members = _merge_member_payloads(members, extra_info, leader_sid=leader_sid, leader_name=rn0)
        
        comp_id = data.get('competition_id')
        if comp_id is None or comp_id == '' or comp_id == 0 or comp_id == '0':
            comp_id = None
        comp = None
        if comp_id is not None:
            try:
                comp_id = int(comp_id)
            except Exception:
                return fail('赛事/批次ID无效', 400)
            comp = conn.execute('SELECT id, title, system_type, template_type FROM competitions WHERE id = ?', (comp_id,)).fetchone()
            comp_title = (comp['title'] if comp else '') or ''
            is_big_challenge = ('挑战杯' in comp_title and '课外学术' in comp_title and '科技作品' in comp_title)
            existing = conn.execute(
                'SELECT id, status FROM projects WHERE created_by = ? AND competition_id = ? ORDER BY id DESC LIMIT 1',
                (user_id, comp_id)
            ).fetchone()
            if existing:
                return fail(
                    '您已报名/暂存过该赛事/批次，请使用“修改报名/修改”入口编辑，避免重复申报',
                    409,
                    data={'existing_project_id': existing['id'], 'existing_status': existing['status']}
                )
            leader_sid = sid0 or un0
            if is_big_challenge and leader_sid:
                mp = conn.execute(
                    '''
                    SELECT p.id, p.status, p.created_by
                    FROM projects p
                    JOIN project_members pm ON pm.project_id = p.id
                    WHERE p.competition_id = ? AND TRIM(pm.student_id) = TRIM(?)
                    ORDER BY p.id DESC LIMIT 1
                    ''',
                    (comp_id, leader_sid)
                ).fetchone()
                if mp and int(mp['created_by']) != int(user_id):
                    return fail(
                        '大挑为团队项目，仅负责人提交一次申报，队员无需重复提交；请直接查看项目或联系负责人修改',
                        409,
                        data={'existing_project_id': mp['id'], 'existing_status': mp['status']}
                    )
        comp_title = (comp['title'] if comp else '') or ''
        comp_system = (comp['system_type'] if comp else '') or ''
        is_dachuang_system = (comp_system in ['创新体系', '创业体系']) or ('创新训练计划' in comp_title) or ('大创' in comp_title)
        is_dachuang_project = is_dachuang_system and p_type in ['innovation', 'entrepreneurship_training', 'entrepreneurship_practice']
        
        if is_dachuang_project and (not is_draft):
            if 1 + len(members) > 5:
                return fail('团队人数≤5人', 400)
            try:
                admission_year = None
                leader_grade = str(data.get('leader_grade') or '').strip()
                if not leader_grade:
                    for m in raw_members:
                        if _is_leader_member(m):
                            leader_grade = str((m or {}).get('grade') or '').strip()
                            break
                m1 = re.match(r'^\s*(\d{4})\s*(?:级)?\s*$', leader_grade)
                if m1:
                    admission_year = int(m1.group(1))
                if admission_year is None and len(sid0) >= 8 and sid0[:4].isdigit():
                    admission_year = int(sid0[:4])
                now = datetime.now()
                academic_year = now.year if now.month >= 9 else (now.year - 1)
                if admission_year is not None and 2000 <= admission_year <= academic_year:
                    grade = academic_year - admission_year + 1
                    if grade > 3:
                        return fail('负责人须为大三及以下', 400)
            except Exception:
                pass
            unfinished = conn.execute(
                """
                SELECT 1 FROM projects
                WHERE created_by = ? AND project_type IN ('innovation','entrepreneurship_training','entrepreneurship_practice')
                  AND status IN ('approved','pending_teacher','pending_college','reviewing','college_recommended',
                                'school_approved','midterm_submitted','midterm_advisor_approved','midterm_college_approved','midterm_approved',
                                'conclusion_submitted','conclusion_advisor_approved','conclusion_college_approved')
                LIMIT 1
                """,
                (user_id,)
            ).fetchone()
            if unfinished:
                return fail('未结题学生不可申报', 400)
                
            try:
                info_obj = extra_info if isinstance(extra_info, dict) else {}
                advisors = info_obj.get('advisors') if isinstance(info_obj.get('advisors'), list) else []
                if p_type == 'innovation':
                    if advisors and isinstance(advisors, list):
                        valid = [a for a in advisors if isinstance(a, dict) and str(a.get('name') or '').strip()]
                        if len(valid) != 1:
                            return fail('大创创新训练项目必须且仅能绑定1名校内指导教师', 400)
                        gt = str(valid[0].get('guidance_type') or '').strip()
                        if gt and gt != '校内导师':
                            return fail('大创创新训练项目指导教师必须为校内导师', 400)
                        data['advisor_name'] = str(valid[0].get('name') or '').strip()
                    else:
                        advisor_name_val = str(data.get('advisor_name') or '').strip()
                        if not advisor_name_val:
                            return fail('大创创新训练项目必须绑定1名校内指导教师', 400)
                    st = str((info_obj.get('special_topic') or '')).strip()
                    if st == 'jiebang':
                        jb_id = info_obj.get('jiebang_topic_id')
                        if not jb_id:
                            return fail('揭榜挂帅专项必须选择对应榜单编号', 400)
                        try:
                            jb_id = int(jb_id)
                        except Exception:
                            return fail('对应榜单编号无效', 400)
                        jb = conn.execute(
                            'SELECT id FROM jiebang_topics WHERE id = ? AND enabled = 1',
                            (jb_id,)
                        ).fetchone()
                        if not jb:
                            return fail('对应榜单编号不存在或已停用', 400)
                if p_type in ['entrepreneurship_training', 'entrepreneurship_practice']:
                    if len(advisors) != 2:
                        return fail('创业类项目指导教师必须2人（校内+校外）', 400)
                    types = [str(a.get('guidance_type') or '').strip() for a in advisors if isinstance(a, dict)]
                    if '校内导师' not in types or '企业导师' not in types:
                        return fail('创业类项目指导教师类型必须包含校内导师与企业导师各1人', 400)
            except Exception:
                return fail('指导教师信息格式错误', 400)

            if p_type in ['entrepreneurship_training', 'entrepreneurship_practice']:
                try:
                    advisor_name_val = str(data.get('advisor_name') or '').strip()
                    if not advisor_name_val:
                        for a in advisors:
                            if not isinstance(a, dict):
                                continue
                            if str(a.get('guidance_type') or '').strip() == '校内导师' and str(a.get('name') or '').strip():
                                advisor_name_val = str(a.get('name') or '').strip()
                                break
                    if advisor_name_val:
                        data['advisor_name'] = advisor_name_val
                except Exception:
                    pass
                
            for m in (members or []):
                sid2 = str(m.get('student_id') or '').strip()
                if not sid2:
                    continue
                cnt2 = conn.execute(
                    """
                    SELECT COUNT(*) as c FROM project_members pm
                    JOIN projects p ON p.id = pm.project_id
                    WHERE pm.student_id = ? AND pm.is_leader = 0
                      AND p.project_type IN ('innovation','entrepreneurship_training','entrepreneurship_practice')
                    """,
                    (sid2,)
                ).fetchone()['c']
                if cnt2 >= 2:
                    return fail(f'成员{m.get("name") or sid2}参与项目已达上限（最多2项）', 400)
        
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
            # 3. 年级限制：负责人须为大三及以下（优先使用“负责人专业年级”）
            try:
                info_obj = extra_info if isinstance(extra_info, dict) else {}
                grade_text = str(info_obj.get('leader_major_grade') or '').strip()
                if not grade_text:
                    grade_text = str(data.get('leader_grade') or '').strip()

                def _parse_grade_num(s: str):
                    if not s:
                        return None
                    if '大一' in s:
                        return 1
                    if '大二' in s:
                        return 2
                    if '大三' in s:
                        return 3
                    if '大四' in s:
                        return 4
                    return None

                gnum = _parse_grade_num(grade_text)
                if gnum is not None:
                    if gnum > 3:
                        return fail('负责人须为大三及以下', 400)
                else:
                    admission_year = None
                    m1 = re.match(r'^\s*(\d{4})\s*(?:级)?\s*$', grade_text)
                    if m1:
                        admission_year = int(m1.group(1))
                    if admission_year is None and len(sid0) >= 8 and sid0[:4].isdigit():
                        admission_year = int(sid0[:4])
                    now = datetime.now()
                    academic_year = now.year if now.month >= 9 else (now.year - 1)
                    if admission_year is not None and 2000 <= admission_year <= academic_year:
                        grade = academic_year - admission_year + 1
                        if grade > 3:
                            return fail('负责人须为大三及以下', 400)
            except Exception:
                pass

        extra_info_json = json.dumps(extra_info)
        
        if not t_type or t_type == 'default':
            t_type = 'innovation' if p_type == 'innovation' else 'startup'

        advisor_name = str(data.get('advisor_name') or '').strip()
        if not advisor_name:
            try:
                info_obj = extra_info if isinstance(extra_info, dict) else {}
                advisors = info_obj.get('advisors')
                if isinstance(advisors, list):
                    for a in advisors:
                        if not isinstance(a, dict):
                            continue
                        if str(a.get('guidance_type') or '').strip() == '校内导师':
                            n = str(a.get('name') or '').strip()
                            if n:
                                advisor_name = n
                                break
                    if not advisor_name:
                        for a in advisors:
                            if isinstance(a, dict):
                                n = str(a.get('name') or '').strip()
                                if n:
                                    advisor_name = n
                                    break
            except Exception:
                advisor_name = ''
            
        # 设置初始状态：大创项目进入导师审核；揭榜挂帅/创业类项目走学校统一评审；暂存为 draft
        initial_status = 'pending'
        if is_draft:
            initial_status = 'draft'
        elif is_dachuang_project:
            st = ''
            try:
                info_obj = extra_info if isinstance(extra_info, dict) else {}
                st = str(info_obj.get('special_topic') or '').strip()
            except Exception:
                st = ''
            if p_type in ['entrepreneurship_training', 'entrepreneurship_practice'] or (p_type == 'innovation' and st == 'jiebang'):
                initial_status = 'under_review'
            else:
                initial_status = 'pending_teacher'
        # 增加日志记录 competition_id 以便调试
        current_app.logger.info(f"Checking initial status: competition_id={comp_id}, p_type={p_type}")
        
        # 更加鲁棒的判断：只要标题或赛事 ID 关联大挑，即进入初审
        if p_type == 'challenge_cup' or (comp_id and '挑战杯' in str(data.get('competition_title', ''))) or '挑战杯' in title:
            initial_status = 'pending_advisor_review'
            current_app.logger.info(f"Project marked as pending_advisor_review")

        cursor = conn.execute('''
            INSERT INTO projects (
                title, leader_name, advisor_name, department, college, 
                project_type, template_type, level, status, year, created_by, abstract, assessment_indicators, competition_id, extra_info, inspiration_source, linked_project_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            title,
            data.get('leader_name', user['real_name']),
            advisor_name,
            data.get('department', user['department']),
            data.get('college', user['college']),
            p_type,
            t_type,
            data.get('level', 'school'),
            initial_status,
            data.get('year', datetime.now().year),
            user_id,
            data.get('abstract', ''),
            data.get('assessment_indicators', ''),
            comp_id,
            extra_info_json,
            data.get('inspiration_source'),
            data.get('linked_project_id')
        ))
        project_id = cursor.lastrowid

        # 初始化过程节点：指导教师初审（针对大挑）
        if initial_status == 'pending_advisor_review':
            conn.execute(
                'INSERT OR REPLACE INTO project_node_status (project_id, node_name, current_status, comment, updated_by, updated_at) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)',
                (project_id, '指导教师初审', '待初审', '', user_id)
            )

        # 借鉴引用：如果前端未标记计数已完成，则在创建项目时给经验库借鉴次数 +1
        inspiration_source = data.get('inspiration_source')
        borrow_counted = bool(data.get('borrow_counted'))
        if inspiration_source and not borrow_counted:
            try:
                legacy_id = int(inspiration_source)
                conn.execute(
                    'UPDATE project_legacy SET borrowed_count = borrowed_count + 1 WHERE id = ?',
                    (legacy_id,)
                )
            except Exception:
                pass
        
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
        leader_sid = sid0 or un0
        conn.execute('INSERT INTO project_members (project_id, is_leader, name, student_id, college, major, grade, role, contact) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (project_id, True, (user['real_name'] or '').strip(), (leader_sid or '').strip(), (user['college'] or '').strip(), (data.get('major', '') or '').strip(), (data.get('leader_grade') or ''), '', (user['email'] or '') or ''))
        
        for m in members:
            conn.execute('INSERT INTO project_members (project_id, is_leader, name, student_id, college, major, grade, role, contact) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                        (project_id, False, str(m.get('name') or '').strip(), str(m.get('student_id') or '').strip(), str(m.get('college') or '').strip(), str(m.get('major') or '').strip(), str(m.get('grade') or '').strip(), str(m.get('role') or '').strip(), str(m.get('contact') or '').strip()))
                        
        # 发送通知
        if not is_draft:
            if initial_status == 'under_review':
                create_role_notifications(conn, ROLES['SCHOOL_APPROVER'], '新项目待评审', f"学生 {user['real_name']} 提交了新项目：{title}，请评审", meta={'route': f'/project/{int(project_id)}', 'project_id': int(project_id)})
                create_role_notifications(conn, ROLES['PROJECT_ADMIN'], '新项目待评审', f"学生 {user['real_name']} 提交了新项目：{title}，请评审", meta={'route': f'/project/{int(project_id)}', 'project_id': int(project_id)})
                if advisor_name:
                    for tid in sorted(set(resolve_teacher_user_ids(conn, advisor_name))):
                        create_notification(conn, tid, '新项目提交提醒', f"学生 {user['real_name']} 提交了新项目：{title}", 'system', meta={'route': f'/project/{int(project_id)}', 'project_id': int(project_id)})
            else:
                if advisor_name:
                    for tid in sorted(set(resolve_teacher_user_ids(conn, advisor_name))):
                        create_notification(conn, tid, '新项目指导申请', f"学生 {user['real_name']} 提交了新项目：{title}，请审核", 'approval', meta={'route': '/', 'query': {'tab': 'my_reviews', 'task': 'advisor_review', 'pid': int(project_id)}, 'project_id': int(project_id)})
        
        conn.commit()
        return success(data={'project_id': project_id}, message='提交成功')
    except Exception as e:
        conn.rollback()
        return fail(str(e), 500)

@projects_bp.route('/projects/<int:project_id>', methods=['GET'])
@login_required
def get_project_detail(project_id):
    user_id = session.get('user_id')
    role = session.get('role')
    conn = get_db_connection()
    project = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    if not project:
        return fail('项目不存在', 404)
    if role == ROLES['STUDENT']:
        if int(project['created_by']) != int(user_id):
            u = conn.execute('SELECT identity_number, real_name, username FROM users WHERE id = ?', (user_id,)).fetchone()
            sid = (u['identity_number'] if u else '') or ''
            rn = (u['real_name'] if u else '') or ''
            un = (u['username'] if u else '') or ''
            ok = None
            cands = []
            for v in [sid, un]:
                vv = str(v or '').strip()
                if vv and vv not in cands:
                    cands.append(vv)
            if cands:
                placeholders = ','.join(['?'] * len(cands))
                ok = conn.execute(
                    f'SELECT 1 FROM project_members WHERE project_id = ? AND TRIM(student_id) IN ({placeholders}) LIMIT 1',
                    [project_id] + cands
                ).fetchone()
            if not ok:
                ok = conn.execute(
                    "SELECT 1 FROM project_members WHERE project_id = ? AND name = ? AND COALESCE(TRIM(student_id),'') = '' LIMIT 1",
                    (project_id, rn)
                ).fetchone()
            if not ok:
                raw = str(project['extra_info'] or '')
                for v in cands:
                    vv = str(v or '').strip()
                    if vv and vv in raw:
                        ok = 1
                        break
            if not ok:
                return fail('无权限查看该项目', 403)
        
    res = dict(project)
    if res.get('extra_info'):
        try:
            res['extra_info'] = json.loads(res['extra_info'])
        except:
            res['extra_info'] = {}
    
    comp_id = res.get('competition_id')
    if comp_id:
        comp = conn.execute(
            'SELECT id, title, system_type, competition_level, template_type, form_config FROM competitions WHERE id = ?',
            (comp_id,)
        ).fetchone()
        if comp:
            comp_dict = dict(comp)
            if comp_dict.get('form_config'):
                try:
                    comp_dict['form_config'] = json.loads(comp_dict['form_config'])
                except Exception:
                    comp_dict['form_config'] = {}
            else:
                comp_dict['form_config'] = {}
            res['competition'] = comp_dict
            if isinstance(comp_dict.get('form_config'), dict):
                res['form_config'] = comp_dict['form_config']
            if comp_dict.get('template_type') and comp_dict.get('template_type') not in ['competition', 'default']:
                res['template_type'] = comp_dict['template_type']

    if res.get('project_type') == 'innovation':
        extra = conn.execute('SELECT * FROM innovation_projects WHERE project_id = ?', (project_id,)).fetchone()
        if extra:
            extra_dict = dict(extra)
            if 'id' in extra_dict:
                del extra_dict['id']
            res.update(extra_dict)
    elif res.get('project_type') in ['entrepreneurship_training', 'entrepreneurship_practice']:
        extra = conn.execute('SELECT * FROM entrepreneurship_projects WHERE project_id = ?', (project_id,)).fetchone()
        if extra:
            extra_dict = dict(extra)
            if 'id' in extra_dict:
                del extra_dict['id']
            res.update(extra_dict)
        
    # 成员
    members = conn.execute('SELECT * FROM project_members WHERE project_id = ?', (project_id,)).fetchall()
    res['members'] = [dict(m) for m in members]
    
    try:
        legacy_row = conn.execute(
            'SELECT id, status, is_public, reject_reason, reviewed_at FROM project_legacy WHERE original_project_id = ? ORDER BY created_at DESC LIMIT 1',
            (project_id,)
        ).fetchone()
        if legacy_row:
            legacy = dict(legacy_row)
            res['legacy_id'] = legacy.get('id')
            res['legacy_status'] = legacy.get('status')
            res['legacy_is_public'] = legacy.get('is_public')
            res['legacy_reject_reason'] = legacy.get('reject_reason')
            res['legacy_reviewed_at'] = legacy.get('reviewed_at')
    except Exception:
        pass
    
    # 评审记录
    reviews = conn.execute('''
        SELECT r.*, u.real_name as judge_name 
        FROM project_reviews r 
        JOIN users u ON r.judge_id = u.id 
        WHERE project_id = ?
    ''', (project_id,)).fetchall()
    res['reviews'] = [dict(r) for r in reviews]
    
    try:
        score_col = 'score'
        try:
            task_cols = [str(c['name']) for c in conn.execute("PRAGMA table_info('review_tasks')").fetchall()]
            if 'total_score' in task_cols:
                score_col = 'total_score'
        except Exception:
            score_col = 'score'
        task_rows = conn.execute(
            f'''
            SELECT t.review_level, t.{score_col} AS total_score, t.comments, t.score_details
            FROM review_tasks t
            WHERE t.project_id = ? AND t.status = 'completed'
              AND t.review_level IN ('college', 'school')
            ORDER BY t.review_level, t.id
            ''',
            (project_id,)
        ).fetchall()
        for tr in task_rows:
            comment_text = (tr['comments'] or '').strip()
            if not comment_text:
                try:
                    details = json.loads(tr['score_details'] or '{}')
                except Exception:
                    details = {}
                reasons = []
                if isinstance(details, dict):
                    for _, item in details.items():
                        if not isinstance(item, dict):
                            continue
                        reason = sanitize_public_text(item.get('reason'))
                        if reason:
                            reasons.append(reason)
                comment_text = '；'.join(reasons).strip()
            if not comment_text:
                continue
            res['reviews'].append({
                'judge_name': '评委',
                'score': tr['total_score'],
                'comment': sanitize_public_text(comment_text)
            })
    except Exception:
        pass
        
    try:
        role = session.get('role')
        if role in [ROLES['STUDENT'], ROLES['TEACHER'], ROLES['COLLEGE_APPROVER'], ROLES['SCHOOL_APPROVER']]:
            for r in res.get('reviews') or []:
                r['judge_name'] = '评委'
    except Exception:
        pass

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

    try:
        row_for_tpl = dict(project)
        comp_id = project['competition_id'] if 'competition_id' in project.keys() else None
        if comp_id:
            comp = conn.execute('SELECT template_type, title FROM competitions WHERE id = ?', (comp_id,)).fetchone()
            if comp:
                row_for_tpl['competition_template_type'] = comp['template_type']
                row_for_tpl['competition_title'] = comp['title']
        tpl_name = resolve_template_name(row_for_tpl)
        if tpl_name == '大挑':
            for lv, fld in [('college', 'college_review_result'), ('school', 'school_review_result')]:
                if res.get(fld) not in [None, '', 'pending']:
                    continue
                tasks = conn.execute(
                    'SELECT status, is_recommended FROM review_tasks WHERE project_id = ? AND review_level = ?',
                    (project_id, lv)
                ).fetchall()
                if not tasks or not all(t['status'] == 'completed' for t in tasks):
                    continue
                recommended_count = sum(1 for t in tasks if int(t['is_recommended'] or 0) == 1)
                is_recommended = 1 if recommended_count > (len(tasks) / 2) else 0
                res[fld] = 'approved' if is_recommended else 'rejected'
            if int(res.get('provincial_advance_national') or 0) == 1:
                res['current_level'] = 'national'
                res['review_stage'] = 'national'
            elif res.get('school_review_result') == 'approved':
                res['current_level'] = 'provincial'
                res['review_stage'] = 'provincial'
            elif res.get('college_review_result') == 'approved':
                res['current_level'] = 'school'
                res['review_stage'] = 'school'
    except Exception:
        pass
    
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
        'dachuang_plan': '大学生创新创业训练计划',
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
        if '大学生创新创业训练计划' in title:
            return '大学生创新创业训练计划'
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
    
    try:
        if tpl['template_name'] == '大挑':
            for lv, node_name in [('college', '学院赛'), ('school', '校赛')]:
                if node_name not in process_structure:
                    continue
                existing = (node_current_status.get(node_name) or '').strip()
                if existing and existing != '待评审':
                    continue
                tasks = conn.execute(
                    'SELECT status, is_recommended FROM review_tasks WHERE project_id = ? AND review_level = ?',
                    (project_id, lv)
                ).fetchall()
                if not tasks:
                    continue
                if not all(t['status'] == 'completed' for t in tasks):
                    continue
                recommended_count = sum(1 for t in tasks if int(t['is_recommended'] or 0) == 1)
                is_recommended = 1 if recommended_count > (len(tasks) / 2) else 0
                node_current_status[node_name] = '已推荐' if is_recommended else '未推荐'
                if is_recommended:
                    idx = process_structure.index(node_name)
                    if idx + 1 < len(process_structure):
                        next_node = process_structure[idx + 1]
                        if not (node_current_status.get(next_node) or '').strip():
                            node_current_status[next_node] = '待评审'
    except Exception:
        pass

    return success(data={
        'template_name': tpl['template_name'],
        'process_structure': process_structure,
        'has_mid_check': bool(tpl['has_mid_check']),
        'has_final_acceptance': bool(tpl['has_final_acceptance']),
        'node_status_options': node_status_options,
        'node_options': node_status_options,
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
        if node_name in ['学院赛', '校赛'] and current_status in ['已推荐', '未推荐']:
            lv_map = {'学院赛': 'college', '校赛': 'school'}
            lv = lv_map.get(node_name)
            if lv:
                tasks = conn.execute(
                    'SELECT status FROM review_tasks WHERE project_id = ? AND review_level = ?',
                    (project_id, lv)
                ).fetchall()
                if not tasks:
                    return fail('该节点暂无评审成绩，不能推荐/未推荐，请先完成评审任务', 400)
                if not all(t['status'] == 'completed' for t in tasks):
                    return fail('评审成绩未全部提交，不能推荐/未推荐，请等待评审完成', 400)
                tasks2 = conn.execute(
                    'SELECT is_recommended FROM review_tasks WHERE project_id = ? AND review_level = ?',
                    (project_id, lv)
                ).fetchall()
                rc = sum(1 for t in tasks2 if int(t['is_recommended'] or 0) == 1)
                rec = 1 if rc > (len(tasks2) / 2) else 0
                expected = '已推荐' if rec else '未推荐'
                if current_status != expected:
                    return fail(f'评审结论为「{expected}」，不能手动改为「{current_status}」', 400)

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

    if template_name == '大挑' and node_name in ['学院赛', '校赛'] and prev_status in ['已推荐', '未推荐']:
        if current_status == prev_status and comment == (prev_comment or '') and award_level == (prev_award_level or ''):
            return success(message='保存成功')
        return fail(f'{node_name}已通过，不能修改', 400)

    from flask import current_app
    current_app.logger.info(f"Updating process node: {node_name}, status: {current_status}, award: {award_level}")

    if template_name == '大挑' and node_name == '省赛' and current_status in ['已晋级', '未晋级']:
        prow = conn.execute('SELECT provincial_award_level FROM projects WHERE id = ?', (project_id,)).fetchone()
        pl = str((prow['provincial_award_level'] if prow else '') or '').strip()
        if not pl or pl == 'none':
            return fail('请先录入省赛获奖等级后，再确认是否晋级国赛', 400)

    conn.execute(
        'INSERT OR REPLACE INTO project_node_status (project_id, node_name, current_status, comment, award_level, updated_by, updated_at) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)',
        (project_id, node_name, current_status, comment, award_level, session.get('user_id'))
    )

    try:
        st_changed = str(prev_status or '').strip() != str(current_status or '').strip()
        c_changed = sanitize_public_text(prev_comment) != sanitize_public_text(comment)
        a_changed = str(prev_award_level or '').strip() != str(award_level or '').strip()
        if st_changed or c_changed or a_changed:
            p_row = conn.execute(
                'SELECT title FROM projects WHERE id = ?',
                (project_id,)
            ).fetchone()
            p_title = sanitize_public_text(p_row['title']) if p_row else str(project_id)
            parts = [f'项目《{p_title}》流程节点更新：{sanitize_public_text(node_name)} → {sanitize_public_text(current_status)}']
            if award_level:
                parts.append(f'获奖等级：{sanitize_public_text(award_level)}')
            c = sanitize_public_text(comment)
            if c:
                parts.append(f'意见：{c[:200]}')
            create_project_related_notifications(
                conn,
                project_id,
                f'流程更新：{sanitize_public_text(node_name)}',
                '；'.join([p for p in parts if p]),
                exclude_user_id=session.get('user_id')
            )
    except Exception:
        pass

    # 同步更新项目主表的整体状态和级别
    if current_status == '已获奖' and award_level and award_level != 'none':
        if node_name == '国赛':
            conn.execute(
                'UPDATE projects SET national_status = ?, national_award_level = ?, status = ?, level = ? WHERE id = ?',
                ('已获奖', award_level, 'finished_national_award', '国赛获奖', project_id)
            )
        elif node_name == '省赛':
            conn.execute(
                'UPDATE projects SET provincial_status = ?, provincial_award_level = ?, level = ? WHERE id = ?',
                ('已获奖', award_level, '省赛获奖', project_id)
            )
    elif current_status == '已晋级' and node_name == '省赛':
        conn.execute(
            'UPDATE projects SET provincial_status = ?, provincial_advance_national = 1, current_level = ?, review_stage = ? WHERE id = ?',
            ('已晋级', 'national', 'national', project_id)
        )
        next_node = '国赛'
        exists_next = conn.execute(
            'SELECT id FROM project_node_status WHERE project_id = ? AND node_name = ?',
            (project_id, next_node)
        ).fetchone()
        if not exists_next:
            conn.execute(
                'INSERT INTO project_node_status (project_id, node_name, current_status, comment, award_level, updated_by, updated_at) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)',
                (project_id, next_node, '待评审', '', '', session.get('user_id'))
            )
    elif current_status == '未晋级' and node_name == '省赛':
        conn.execute(
            'UPDATE projects SET provincial_status = ?, provincial_advance_national = 0, status = ?, level = ?, current_level = ?, review_stage = ? WHERE id = ?',
            ('未晋级', 'provincial_award', '省赛获奖', 'provincial', 'provincial', project_id)
        )
        try:
            conn.execute(
                'UPDATE project_node_status SET current_status = ? WHERE project_id = ? AND node_name = ?',
                ('', project_id, '国赛')
            )
        except Exception:
            pass
    elif template_name == '大挑' and node_name == '国赛' and current_status == '未获奖':
        conn.execute(
            'UPDATE projects SET status = ? WHERE id = ?',
            ('finished', project_id)
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
                create_notification(
                    conn,
                    m['user_id'],
                    '新增校赛评审任务',
                    f'项目《{p_row["title"]}》已进入校赛，请在“我的评审任务”中完成评审。',
                    'project',
                    meta={'route': '/', 'query': {'tab': 'my_reviews', 'task': 'review_task', 'pid': int(project_id)}, 'project_id': int(project_id)}
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

    if template_name == '大挑' and node_name == '学院赛' and current_status == '未推荐':
        p_row = conn.execute(
            'SELECT id, title, created_by FROM projects WHERE id = ?',
            (project_id,)
        ).fetchone()
        p_dict = dict(p_row) if p_row else {}
        conn.execute(
            'UPDATE projects SET status = ?, college_review_result = ?, college_result_locked = 1, current_level = ?, review_stage = ? WHERE id = ?',
            ('college_failed', 'rejected', 'college', 'college', project_id)
        )
        try:
            conn.execute(
                "UPDATE project_node_status SET current_status = '' WHERE project_id = ? AND node_name IN ('校赛','省赛','国赛')",
                (project_id,)
            )
        except Exception:
            pass
        if p_dict.get('created_by'):
            try:
                create_notification(conn, int(p_dict['created_by']), '学院赛未通过', f'你的项目《{p_dict.get("title") or ""}》学院赛未通过，感谢参与。', 'project')
            except Exception:
                pass

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

    if template_name == '大挑' and node_name == '校赛' and current_status == '未推荐':
        p_row = conn.execute(
            'SELECT id, title, created_by FROM projects WHERE id = ?',
            (project_id,)
        ).fetchone()
        p_dict = dict(p_row) if p_row else {}
        conn.execute(
            'UPDATE projects SET status = ?, school_review_result = ?, school_result_locked = 1, current_level = ?, review_stage = ? WHERE id = ?',
            ('school_failed', 'rejected', 'school', 'school', project_id)
        )
        try:
            conn.execute(
                "UPDATE project_node_status SET current_status = '' WHERE project_id = ? AND node_name IN ('省赛','国赛')",
                (project_id,)
            )
        except Exception:
            pass
        if p_dict.get('created_by'):
            try:
                create_notification(conn, int(p_dict['created_by']), '校赛未通过', f'你的项目《{p_dict.get("title") or ""}》校赛未晋级，可申报校赛奖项。', 'project')
            except Exception:
                pass
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
    if not advisor_name:
        try:
            advisors = info.get('advisors')
            if isinstance(advisors, list) and advisors:
                for a in advisors:
                    if isinstance(a, dict) and str(a.get('guidance_type') or '').strip() == '校内导师':
                        n = str(a.get('name') or '').strip()
                        if n:
                            advisor_name = n
                            break
                if not advisor_name:
                    for a in advisors:
                        if isinstance(a, dict):
                            n = str(a.get('name') or '').strip()
                            if n:
                                advisor_name = n
                                break
        except Exception:
            advisor_name = advisor_name
    if advisor_name:
        for tid in resolve_teacher_user_ids(conn, advisor_name):
            create_notification(conn, tid, '中期材料待审核', f"项目 {project['title']} 提交了中期材料，请审核", 'approval', meta={'route': f'/project/{int(project_id)}', 'project_id': int(project_id)})

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
    if not advisor_name:
        try:
            advisors = info.get('advisors')
            if isinstance(advisors, list) and advisors:
                for a in advisors:
                    if isinstance(a, dict) and str(a.get('guidance_type') or '').strip() == '校内导师':
                        n = str(a.get('name') or '').strip()
                        if n:
                            advisor_name = n
                            break
                if not advisor_name:
                    for a in advisors:
                        if isinstance(a, dict):
                            n = str(a.get('name') or '').strip()
                            if n:
                                advisor_name = n
                                break
        except Exception:
            advisor_name = advisor_name
    if advisor_name:
        for tid in resolve_teacher_user_ids(conn, advisor_name):
            create_notification(conn, tid, '结题材料待审核', f"项目 {project['title']} 提交了结题材料，请审核", 'approval', meta={'route': f'/project/{int(project_id)}', 'project_id': int(project_id)})

    conn.commit()
    return success(message='结题材料提交成功')


@projects_bp.route('/projects/<int:project_id>/methodology', methods=['POST'])
@login_required
def submit_methodology(project_id):
    if project_id in GHOST_PROJECT_IDS:
        return fail('项目不存在', 404)

    user_id = session.get('user_id')
    role = session.get('role')
    if role != ROLES['STUDENT']:
        return fail('无权限', 403)

    conn = get_db_connection()
    project = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    if not project:
        return fail('项目不存在', 404)
    if project['created_by'] != user_id:
        return fail('无权限', 403)

    data = request.json or {}
    sections = data.get('sections') or {}
    if sections and not isinstance(sections, dict):
        return fail('sections 格式错误', 400)
    section_titles = data.get('section_titles') or {}
    if section_titles and not isinstance(section_titles, dict):
        return fail('section_titles 格式错误', 400)
    safe_sections = {}
    if isinstance(sections, dict) and sections:
        for k, v in sections.items():
            safe_sections[str(k)] = sanitize_rich_html(str(v or ''))
    summary = sanitize_public_text(data.get('summary'))
    attachments = data.get('attachments') or {}
    if not isinstance(attachments, dict):
        return fail('attachments 格式错误', 400)
    if safe_sections:
        parts = []
        i = 1
        for k, html in safe_sections.items():
            plain = sanitize_public_text(strip_html(html))
            if not plain:
                continue
            title = str(section_titles.get(k) or k).strip()
            parts.append(f'{i}. {title}：{plain}')
            i += 1
        if not parts:
            return fail('富文本内容不能为空', 400)
        summary = '\n'.join(parts)
    if not summary:
        return fail('方法论总结不能为空', 400)
    if len(summary) > 8000:
        return fail('方法论总结过长', 400)

    try:
        info = json.loads(project['extra_info']) if project['extra_info'] else {}
    except Exception:
        info = {}

    try:
        resolved_template = resolve_template_name(dict(project))
    except Exception:
        resolved_template = None
    if not is_experience_eligible(dict(project), info, resolved_template):
        return fail('当前项目不符合经验提交流程（需优秀/获奖项目）', 400)
    if (resolved_template or '').strip() == '大学生创新创业训练计划':
        derived_category = 'innovation' if (project.get('project_type') or '') == 'innovation' else 'entrepreneurship'
    else:
        derived_category = legacy_category_from_template(resolved_template)

    if (project['project_type'] or '') == 'challenge_cup' or resolved_template == '大挑':
        if not (str(attachments.get('route_map') or '').strip()):
            return fail('大挑项目技术路线图/研究框架图为必传材料', 400)

    info['methodology_summary'] = summary
    if safe_sections:
        info['methodology_sections'] = safe_sections
    info['methodology_attachments'] = {k: str(v) for k, v in attachments.items() if v}
    info['methodology_submitted_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    info['experience_status'] = 'pending_teacher'
    if resolved_template:
        info['experience_template_name'] = resolved_template

    for k, url in info['methodology_attachments'].items():
        if url:
            existing = conn.execute(
                'SELECT id FROM project_files WHERE project_id = ? AND file_type = ? AND file_path = ?',
                (project_id, 'methodology', url)
            ).fetchone()
            if not existing:
                filename = str(url).split('/')[-1]
                st = 'pending'
                conn.execute(
                    "INSERT INTO project_files (project_id, file_type, file_path, original_filename, status) VALUES (?, 'methodology', ?, ?, ?)",
                    (project_id, url, filename, st)
                )

    conn.execute('UPDATE projects SET extra_info = ? WHERE id = ?', (json.dumps(info, ensure_ascii=False), project_id))
    try:
        existing_legacy = conn.execute(
            "SELECT id, status FROM project_legacy WHERE original_project_id = ? AND project_category = ?",
            (project_id, derived_category)
        ).fetchone()
        if not existing_legacy:
            try:
                auto_collect_legacy(conn, project_id, user_id)
            except Exception:
                pass
            existing_legacy = conn.execute(
                "SELECT id, status FROM project_legacy WHERE original_project_id = ? AND project_category = ?",
                (project_id, derived_category)
            ).fetchone()
        if existing_legacy:
            experience_sections = None
            try:
                if safe_sections:
                    experience_sections = json.dumps(safe_sections, ensure_ascii=False)
            except Exception:
                experience_sections = None
            conn.execute(
                '''
                UPDATE project_legacy
                SET methodology_summary = ?, project_summary = ?, expert_comments = ?, status = 'pending_teacher', is_public = 0,
                    reviewed_by = NULL, reviewed_at = NULL, reject_reason = NULL
                WHERE id = ?
                ''',
                (summary, sanitize_public_text(dict(project).get('abstract') or ''), get_review_task_comments_for_project(conn, project_id), existing_legacy['id'])
            )
            try:
                conn.execute(
                    'UPDATE project_legacy SET template_name = ?, experience_sections = ? WHERE id = ?',
                    (resolved_template, experience_sections, existing_legacy['id'])
                )
            except Exception:
                pass
            try:
                sync_methodology_attachments_to_legacy(conn, project_id, existing_legacy['id'], info.get('methodology_attachments') or {}, user_id)
            except Exception:
                pass
    except Exception:
        pass
    try:
        info = append_experience_audit_log(info, role='student', action='submit', opinion='提交经验内容', reviewer_id=user_id)
        conn.execute('UPDATE projects SET extra_info = ? WHERE id = ?', (json.dumps(info, ensure_ascii=False), project_id))
        advisor_name = str(dict(project).get('advisor_name') or '').strip()
        if advisor_name:
            tids = set(resolve_teacher_user_ids(conn, advisor_name))
            for tid in tids:
                create_notification(conn, tid, '待导师审核经验内容', f"项目《{project['title']}》经验内容已提交，请进行导师审核。", 'approval', meta={'project_id': project_id})
        create_notification(conn, user_id, '经验内容提交成功', f"项目《{project['title']}》已提交，当前状态：待导师审核。", 'system', meta={'project_id': project_id})
        conn.commit()
        return success(message='方法论总结提交成功')
    except Exception as e:
        conn.rollback()
        return fail(str(e), 500)

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
    if role == ROLES['STUDENT'] and int(project['created_by']) != int(user_id):
        return fail('仅项目负责人可修改/提交；队员账号仅可查看项目', 403)
        
    data = request.json
    is_draft = bool(data.get('is_draft'))
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

    comp_id = data.get('competition_id') or project.get('competition_id')
    comp = None
    if comp_id:
        comp = conn.execute('SELECT id, title, system_type FROM competitions WHERE id = ?', (comp_id,)).fetchone()
    comp_title = (comp['title'] if comp else '') or ''
    comp_system = (comp['system_type'] if comp else '') or ''
    is_dachuang_system = (comp_system in ['创新体系', '创业体系']) or ('创新训练计划' in comp_title) or ('大创' in comp_title)
    is_dachuang_project = is_dachuang_system and p_type in ['innovation', 'entrepreneurship_training', 'entrepreneurship_practice']
    if is_dachuang_project and (not is_draft):
        members_for_limit = data.get('members', []) or []
        if role == ROLES['STUDENT']:
            u0 = conn.execute('SELECT identity_number, real_name, username FROM users WHERE id = ?', (user_id,)).fetchone()
            sid0 = str((u0['identity_number'] if u0 else '') or '').strip()
            un0 = str((u0['username'] if u0 else '') or '').strip()
            rn0 = str((u0['real_name'] if u0 else '') or '').strip()
            leader_sid0 = sid0 or un0
            members_for_limit = _merge_member_payloads(members_for_limit, extra_info, leader_sid=leader_sid0, leader_name=rn0)
        if 1 + len(members_for_limit) > 5:
            return fail('团队人数≤5人', 400)
        try:
            info_obj = extra_info if isinstance(extra_info, dict) else {}
            advisors = info_obj.get('advisors') if isinstance(info_obj.get('advisors'), list) else []
            if p_type == 'innovation':
                if advisors and isinstance(advisors, list):
                    valid = [a for a in advisors if isinstance(a, dict) and str(a.get('name') or '').strip()]
                    if len(valid) != 1:
                        return fail('大创创新训练项目必须且仅能绑定1名校内指导教师', 400)
                    gt = str(valid[0].get('guidance_type') or '').strip()
                    if gt and gt != '校内导师':
                        return fail('大创创新训练项目指导教师必须为校内导师', 400)
                    data['advisor_name'] = str(valid[0].get('name') or '').strip()
                else:
                    advisor_name_val = str(data.get('advisor_name') or '').strip()
                    if not advisor_name_val:
                        return fail('大创创新训练项目必须绑定1名校内指导教师', 400)
                st = str((info_obj.get('special_topic') or '')).strip()
                if st == 'jiebang':
                    jb_id = info_obj.get('jiebang_topic_id')
                    if not jb_id:
                        return fail('揭榜挂帅专项必须选择对应榜单编号', 400)
                    try:
                        jb_id = int(jb_id)
                    except Exception:
                        return fail('对应榜单编号无效', 400)
                    jb = conn.execute(
                        'SELECT id FROM jiebang_topics WHERE id = ? AND enabled = 1',
                        (jb_id,)
                    ).fetchone()
                    if not jb:
                        return fail('对应榜单编号不存在或已停用', 400)
            if p_type in ['entrepreneurship_training', 'entrepreneurship_practice']:
                if len(advisors) != 2:
                    return fail('创业类项目指导教师必须2人（校内+校外）', 400)
                types = [str(a.get('guidance_type') or '').strip() for a in advisors if isinstance(a, dict)]
                if '校内导师' not in types or '企业导师' not in types:
                    return fail('创业类项目指导教师类型必须包含校内导师与企业导师各1人', 400)
        except Exception:
            return fail('指导教师信息格式错误', 400)

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
            
        if project['status'] not in ['draft', 'pending', 'pending_teacher', 'pending_college', 'rejected', 'advisor_approved', 'college_approved', 'pending_advisor_review', 'to_modify']:
            return fail('当前状态无法修改', 400)
    
    try:
        new_status = project['status']
        if role == ROLES['STUDENT']:
            if is_draft:
                new_status = 'draft'
            else:
                new_status = 'pending_teacher' if is_dachuang_project else 'pending'
            if p_type == 'challenge_cup' or '挑战杯' in str(data.get('title', '')):
                new_status = 'pending_advisor_review'
                
            if project['status'] == 'school_approved':
                new_status = 'school_approved'

        new_competition_id = project['competition_id']
        if 'competition_id' in data:
            v = data.get('competition_id')
            if v is None or v == '' or v == 0 or v == '0':
                new_competition_id = None
            else:
                try:
                    new_competition_id = int(v)
                except Exception:
                    return fail('赛事/批次ID无效', 400)
        
        conn.execute('''
            UPDATE projects SET 
                title=?, leader_name=?, advisor_name=?, department=?, college=?,
                project_type=?, level=?, year=?, abstract=?, assessment_indicators=?,
                competition_id=?, extra_info=?, status=?
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
            new_competition_id,
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

        leader_member_in_payload = None
        for m in data.get('members', []) or []:
            if m and m.get('student_id') and str(m.get('student_id')) == str(leader_id):
                leader_member_in_payload = m
                break

        leader_grade = (leader_member_in_payload or {}).get('grade')
        if not leader_grade and current_leader_member:
            leader_grade = current_leader_member['grade']
        leader_role = (leader_member_in_payload or {}).get('role') or 'leader'

        conn.execute('''
            INSERT INTO project_members (
                project_id, is_leader, name, student_id, college, major, grade, role, contact
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            project_id, True, leader_name, leader_id, leader_college, leader_major, leader_grade, leader_role, leader_contact
        ))
        members_to_store = _merge_member_payloads(data.get('members', []) or [], extra_info, leader_sid=leader_id, leader_name=leader_name)
        for m in members_to_store:
            conn.execute(
                'INSERT INTO project_members (project_id, is_leader, name, student_id, college, major, grade, role, contact) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (project_id, False, m.get('name'), m.get('student_id'), m.get('college'), m.get('major'), m.get('grade'), (m.get('role') or 'member'), (m.get('contact') or ''))
            )
                        
        if role == ROLES['STUDENT'] and (not is_draft):
            try:
                old_status = str(project['status'] or '').strip()
                ns = str(new_status or '').strip()
                if old_status != ns and ns in ['pending_teacher', 'pending_advisor_review', 'under_review', 'pending']:
                    u = conn.execute('SELECT real_name FROM users WHERE id = ?', (user_id,)).fetchone()
                    student_name = sanitize_public_text(u['real_name']) if u else ''
                    p_title = sanitize_public_text(data.get('title') or project.get('title') or '')

                    advisor_name_val = str(data.get('advisor_name') or project.get('advisor_name') or '').strip()
                    if not advisor_name_val:
                        try:
                            info_obj = extra_info if isinstance(extra_info, dict) else {}
                            advisors = info_obj.get('advisors') if isinstance(info_obj.get('advisors'), list) else []
                            if isinstance(advisors, list) and advisors:
                                preferred = ''
                                for a in advisors:
                                    if isinstance(a, dict) and str(a.get('guidance_type') or '').strip() == '校内导师':
                                        preferred = str(a.get('name') or '').strip()
                                        if preferred:
                                            break
                                if not preferred:
                                    for a in advisors:
                                        if isinstance(a, dict):
                                            preferred = str(a.get('name') or '').strip()
                                            if preferred:
                                                break
                                advisor_name_val = preferred or advisor_name_val
                        except Exception:
                            advisor_name_val = advisor_name_val

                    if ns == 'under_review':
                        create_role_notifications(conn, ROLES['SCHOOL_APPROVER'], '项目已修改重报待评审', f"学生 {student_name} 修改重报了项目：{p_title}，请评审", meta={'route': f'/project/{int(project_id)}', 'project_id': int(project_id)})
                        create_role_notifications(conn, ROLES['PROJECT_ADMIN'], '项目已修改重报待评审', f"学生 {student_name} 修改重报了项目：{p_title}，请评审", meta={'route': f'/project/{int(project_id)}', 'project_id': int(project_id)})
                        if advisor_name_val:
                            for tid in sorted(set(resolve_teacher_user_ids(conn, advisor_name_val))):
                                create_notification(conn, tid, '项目修改重报提醒', f"学生 {student_name} 修改重报了项目：{p_title}", 'system', meta={'route': f'/project/{int(project_id)}', 'project_id': int(project_id)})
                    else:
                        if advisor_name_val:
                            for tid in sorted(set(resolve_teacher_user_ids(conn, advisor_name_val))):
                                create_notification(conn, tid, '项目修改重报待审核', f"学生 {student_name} 修改重报了项目：{p_title}，请审核", 'approval', meta={'route': '/', 'query': {'tab': 'my_reviews', 'task': 'advisor_review', 'pid': int(project_id)}, 'project_id': int(project_id)})
            except Exception:
                pass

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
        
    if not feedback or not feedback.strip():
        return fail('审批意见为必填项', 400)
        
    conn = get_db_connection()
    project = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    if not project:
        return fail('项目不存在', 404)
        
    try:
        if role == ROLES['COLLEGE_APPROVER']:
            conn.execute('UPDATE projects SET status = ?, college_feedback = ? WHERE id = ?', (new_status, feedback, project_id))
        else:
            conn.execute('UPDATE projects SET status = ?, school_feedback = ? WHERE id = ?', (new_status, feedback, project_id))
            # 关键修复：如果状态被设置为 rated (立项)，同步更新层级和阶段
            if new_status == 'rated':
                conn.execute(
                    'UPDATE projects SET current_level = ?, review_stage = ? WHERE id = ?',
                    ('school', 'school', project_id)
                )
            
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
    u = conn.execute('SELECT identity_number, real_name, username FROM users WHERE id = ?', (user_id,)).fetchone()
    sid = (u['identity_number'] if u else '') or ''
    rn = (u['real_name'] if u else '') or ''
    un = (u['username'] if u else '') or ''

    query = '''
        SELECT id, title, status, level, created_at
        FROM projects
        WHERE template_type = 'training'
    '''
    params = []
    if GHOST_PROJECT_IDS:
        query += f" AND id NOT IN ({','.join(map(str, GHOST_PROJECT_IDS))})"
    cands = []
    for v in [sid, un]:
        vv = str(v or '').strip()
        if vv and vv not in cands:
            cands.append(vv)
    if cands:
        placeholders = ','.join(['?'] * len(cands))
        query += f" AND (created_by = ? OR id IN (SELECT project_id FROM project_members WHERE TRIM(student_id) IN ({placeholders})) OR id IN (SELECT project_id FROM project_members WHERE name = ? AND COALESCE(TRIM(student_id),'') = ''))"
        params.extend([user_id] + cands + [rn])
    else:
        query += " AND (created_by = ? OR id IN (SELECT project_id FROM project_members WHERE name = ? AND COALESCE(TRIM(student_id),'') = ''))"
        params.extend([user_id, rn])
    query += " ORDER BY created_at DESC"

    rows = conn.execute(query, params).fetchall()
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
    if s in ['特等', 'special', '特等奖']:
        return 'special'
    if s in ['一等', 'first', '一等奖']:
        return 'first'
    if s in ['二等', 'second', '二等奖']:
        return 'second'
    if s in ['三等', 'third', '三等奖']:
        return 'third'
    if s in ['优秀奖', 'excellent']:
        return 'excellent'
    if s in ['无', 'none']:
        return 'none'
    return (v or '').strip()

def award_level_code_to_label(v):
    s = (v or '').strip().lower()
    if s == 'gold':
        return '金奖'
    if s == 'silver':
        return '银奖'
    if s == 'bronze':
        return '铜奖'
    if s == 'special':
        return '特等奖'
    if s == 'first':
        return '一等奖'
    if s == 'second':
        return '二等奖'
    if s == 'third':
        return '三等奖'
    if s == 'excellent':
        return '优秀奖'
    if s == 'none':
        return ''
    return v or ''

def auto_collect_legacy(conn, project_id, submitted_by):
    project_row = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    if not project_row:
        return
    project = dict(project_row)
    try:
        resolved_template = resolve_template_name(project)
        if (resolved_template or '').strip() == '大学生创新创业训练计划':
            derived_category = 'innovation' if (project.get('project_type') or '') == 'innovation' else 'entrepreneurship'
        else:
            derived_category = legacy_category_from_template(resolved_template)
    except Exception:
        resolved_template = ''
        derived_category = 'innovation'
    
    try:
        info = json.loads(project.get('extra_info') or '{}')
    except Exception:
        info = {}
    if not is_legacy_collection_ready(project, info, resolved_template):
        return
    award_level = normalize_award_level(get_award_level_for_project(project))
        
    exists = conn.execute(
        'SELECT id FROM project_legacy WHERE original_project_id = ? AND project_category = ?',
        (project_id, derived_category)
    ).fetchone()
    if exists:
        return
        
    title = sanitize_public_text(project.get('title') or '')
    project_summary = sanitize_public_text(project.get('abstract') or '')
    methodology_summary = sanitize_public_text(info.get('methodology_summary') or '')
    expert_comments = get_review_task_comments_for_project(conn, project_id)
    industry_field = ''
    team_experience = ''
    pitfalls = ''
    experience_sections = ''
    try:
        if isinstance(info.get('methodology_sections'), dict):
            experience_sections = json.dumps(info.get('methodology_sections') or {}, ensure_ascii=False)
    except Exception:
        experience_sections = ''
        
    legacy_competition_type = legacy_competition_type_from_template(
        resolved_template,
        project.get('project_type'),
        derived_category
    )
    conn.execute(
        '''
        INSERT INTO project_legacy (
            original_project_id, project_category, project_type, award_level,
            title, project_summary, methodology_summary, expert_comments, industry_field,
            team_experience, pitfalls, is_public, status, submitted_by, template_name, experience_sections
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'unsubmitted', ?, ?, ?)
        ''',
        (
            project_id,
            derived_category,
            legacy_competition_type,
            award_level,
            title,
            project_summary,
            methodology_summary,
            expert_comments,
            industry_field,
            team_experience,
            pitfalls,
            submitted_by,
            resolved_template,
            experience_sections
        )
    )

def sync_methodology_attachments_to_legacy(conn, project_id, legacy_id, attachments, user_id):
    if not isinstance(attachments, dict):
        return
        
    base = current_app.config.get('UPLOAD_FOLDER') or 'static/uploads'
    if not os.path.isabs(base):
        project_root = os.path.abspath(os.path.join(current_app.root_path, '..'))
        base = os.path.join(project_root, base)
    legacy_dir = os.path.join(base, 'legacy')
    os.makedirs(legacy_dir, exist_ok=True)
    
    def url_to_path(url):
        u = str(url or '')
        if not u:
            return None
        if u.startswith('/static/uploads/'):
            filename = u.split('/')[-1]
            return os.path.join(base, filename)
        return None
    
    for key, url in attachments.items():
        src = url_to_path(url)
        if not src or not os.path.exists(src):
            continue
        original_filename = os.path.basename(src)
        exists = conn.execute(
            'SELECT id FROM legacy_files WHERE legacy_id = ? AND file_type = ? AND original_filename = ?',
            (legacy_id, key, original_filename)
        ).fetchone()
        if exists:
            continue
        ts = datetime.now().strftime('%Y%m%d%H%M%S%f')
        stored_name = f'{legacy_id}_{key}_{ts}_{original_filename}'
        dst = os.path.join(legacy_dir, stored_name)
        try:
            shutil.copy2(src, dst)
        except Exception:
            continue
            
        status = 'pending'
        reviewed_by = None
        reviewed_at = None
        reject_reason = None
            
        conn.execute(
            '''
            INSERT INTO legacy_files (legacy_id, file_type, stored_path, original_filename, uploaded_by, status, reviewed_by, reviewed_at, reject_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (legacy_id, key, dst, original_filename, user_id, status, reviewed_by, reviewed_at, reject_reason)
        )

def sync_award_to_project_results(conn, project_id, stage, award_level, user_id, recommend_national=0):
    al = normalize_award_level(award_level)
    stage = normalize_review_stage(stage)
    if stage not in ['provincial', 'national']:
        return

    rec = 1 if str(recommend_national or '').lower() in ['1', 'true', 'yes'] else 0
        
    if stage == 'provincial':
        if al and al != 'none':
            if rec:
                conn.execute(
                    '''
                    UPDATE projects
                    SET provincial_status = ?,
                        provincial_award_level = ?,
                        provincial_advance_national = 1,
                        national_status = COALESCE(NULLIF(national_status, ''), '未参赛'),
                        national_award_level = COALESCE(NULLIF(national_award_level, ''), 'none'),
                        current_level = ?,
                        review_stage = ?
                    WHERE id = ?
                    ''',
                    ('已获奖', al, 'national', 'national', project_id)
                )
                conn.execute(
                    '''
                    INSERT OR REPLACE INTO project_node_status
                    (project_id, node_name, current_status, comment, award_level, updated_by, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ''',
                    (project_id, '省赛', '已晋级', '', award_level_code_to_label(al), user_id)
                )
                conn.execute(
                    '''
                    INSERT OR REPLACE INTO project_node_status
                    (project_id, node_name, current_status, comment, award_level, updated_by, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ''',
                    (project_id, '国赛', '待评审', '', '', user_id)
                )
            else:
                p = None
                try:
                    p = conn.execute(
                        'SELECT national_status, national_award_level, current_level, review_stage FROM projects WHERE id = ?',
                        (project_id,)
                    ).fetchone()
                except Exception:
                    p = None
                nat_status = str((p['national_status'] if p else '') or '').strip()
                nat_level = normalize_award_level((p['national_award_level'] if p else '') or '')
                has_nat_award = (nat_status == '已获奖') or (nat_level and nat_level != 'none')

                if has_nat_award:
                    conn.execute(
                        '''
                        UPDATE projects
                        SET provincial_status = ?,
                            provincial_award_level = ?,
                            provincial_advance_national = 1
                        WHERE id = ?
                        ''',
                        ('已获奖', al, project_id)
                    )
                else:
                    conn.execute(
                        '''
                        UPDATE projects
                        SET provincial_status = ?,
                            provincial_award_level = ?,
                            provincial_advance_national = 0,
                            current_level = ?,
                            review_stage = ?
                        WHERE id = ?
                        ''',
                        ('已获奖', al, 'provincial', 'provincial', project_id)
                    )
                    try:
                        conn.execute(
                            '''
                            UPDATE project_node_status
                            SET current_status = '', comment = '', award_level = '', updated_by = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE project_id = ? AND node_name = ?
                            ''',
                            (user_id, project_id, '国赛')
                        )
                    except Exception:
                        pass
                conn.execute(
                    '''
                    INSERT OR REPLACE INTO project_node_status
                    (project_id, node_name, current_status, comment, award_level, updated_by, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ''',
                    (project_id, '省赛', '未晋级', '', award_level_code_to_label(al), user_id)
                )
        else:
            conn.execute(
                '''
                UPDATE projects
                SET provincial_status = ?,
                    provincial_award_level = ?,
                    provincial_advance_national = 0
                WHERE id = ?
                ''',
                ('已参赛', al or 'none', project_id)
            )
            conn.execute(
                '''
                INSERT OR REPLACE INTO project_node_status
                (project_id, node_name, current_status, comment, award_level, updated_by, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''',
                (project_id, '省赛', '未晋级', '', '', user_id)
            )
    else:
        if al and al != 'none':
            conn.execute(
                '''
                UPDATE projects
                SET national_status = ?,
                    national_award_level = ?,
                    status = ?,
                    level = ?
                WHERE id = ?
                ''',
                ('已获奖', al, 'finished_national_award', '国赛获奖', project_id)
            )
            conn.execute(
                '''
                INSERT OR REPLACE INTO project_node_status
                (project_id, node_name, current_status, comment, award_level, updated_by, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''',
                (project_id, '国赛', '已获奖', '', award_level_code_to_label(al), user_id)
            )
        else:
            conn.execute(
                '''
                UPDATE projects
                SET national_status = ?,
                    national_award_level = ?
                WHERE id = ?
                ''',
                ('已参赛', al or 'none', project_id)
            )
            conn.execute(
                '''
                INSERT OR REPLACE INTO project_node_status
                (project_id, node_name, current_status, comment, award_level, updated_by, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''',
                (project_id, '国赛', '未获奖', '', '', user_id)
            )

    try:
        auto_collect_legacy(conn, project_id, user_id)
    except Exception:
        pass


def can_view_project(conn, role, user_id, project_row):
    if role == ROLES['STUDENT']:
        try:
            if int(project_row.get('created_by') or 0) == int(user_id or 0):
                return True
        except Exception:
            pass
        u = conn.execute('SELECT identity_number, real_name, username FROM users WHERE id = ?', (user_id,)).fetchone()
        sid = (u['identity_number'] if u else '') or ''
        rn = (u['real_name'] if u else '') or ''
        un = (u['username'] if u else '') or ''
        cands = []
        for v in [sid, un]:
            vv = str(v or '').strip()
            if vv and vv not in cands:
                cands.append(vv)
        ok = None
        if cands:
            placeholders = ','.join(['?'] * len(cands))
            ok = conn.execute(
                f'SELECT 1 FROM project_members WHERE project_id = ? AND TRIM(student_id) IN ({placeholders}) LIMIT 1',
                [project_row.get('id')] + cands
            ).fetchone()
        if not ok:
            ok = conn.execute(
                "SELECT 1 FROM project_members WHERE project_id = ? AND name = ? AND COALESCE(TRIM(student_id),'') = '' LIMIT 1",
                (project_row.get('id'), rn)
            ).fetchone()
        return bool(ok)
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

    pd = dict(project)
    advisor_op = ''
    try:
        advisor_op = (project['advisor_review_opinion'] or '').strip()
    except Exception:
        advisor_op = ''
    dept_op = (project['department_head_opinion'] or '').strip()
    if not dept_op and advisor_op:
        dept_op = advisor_op

    data = {
        'review_stage': project['review_stage'],
        'college_review_result': project['college_review_result'],
        'school_review_result': project['school_review_result'],
        'provincial_award_level': project['provincial_award_level'],
        'national_award_level': project['national_award_level'],
        'research_admin_opinion': project['research_admin_opinion'],
        'department_head_opinion': dept_op,
        'advisor_review_opinion': advisor_op,
        'college_result_locked': int(pd.get('college_result_locked') or 0),
        'school_result_locked': int(pd.get('school_result_locked') or 0)
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
    return fail('该区域已锁定，只展示同步结果；请在评审管理/过程管理/获奖记录中操作', 400)

    try:
        pd = dict(project)
        if int(pd.get('college_result_locked') or 0) == 1:
            if 'college_review_result' in data:
                if normalize_review_result(data.get('college_review_result')) != normalize_review_result(pd.get('college_review_result')):
                    return fail('学院赛结果已锁定，相关信息不可修改', 400)
            if 'department_head_opinion' in data:
                if str((data.get('department_head_opinion') or '')).strip() != str((pd.get('department_head_opinion') or '')).strip():
                    return fail('学院赛结果已锁定，相关信息不可修改', 400)
        if int(pd.get('school_result_locked') or 0) == 1:
            if 'school_review_result' in data:
                if normalize_review_result(data.get('school_review_result')) != normalize_review_result(pd.get('school_review_result')):
                    return fail('校赛结果已锁定，相关信息不可修改', 400)
            if 'research_admin_opinion' in data:
                if str((data.get('research_admin_opinion') or '')).strip() != str((pd.get('research_admin_opinion') or '')).strip():
                    return fail('校赛结果已锁定，相关信息不可修改', 400)
    except Exception:
        pass

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
            'department_head_opinion'
        }
    elif role == ROLES['COLLEGE_APPROVER']:
        editable = {'college_review_result', 'department_head_opinion'}
    elif role == ROLES['SCHOOL_APPROVER']:
        editable = {'review_stage', 'school_review_result', 'provincial_award_level', 'national_award_level'}
    elif role == ROLES['JUDGE']:
        editable = {'review_stage', 'college_review_result', 'school_review_result', 'department_head_opinion'}

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

    if 'department_head_opinion' in editable and 'department_head_opinion' in data:
        updates['department_head_opinion'] = (data.get('department_head_opinion') or '').strip()

    if not updates:
        return success(message='无可更新字段')

    try:
        sets = ', '.join([f"{k} = ?" for k in updates.keys()])
        params = list(updates.values()) + [project_id]
        conn.execute(f'UPDATE projects SET {sets} WHERE id = ?', params)
        if template_name == '大挑' and updates.get('college_review_result') == 'rejected':
            conn.execute(
                'UPDATE projects SET status = ?, college_result_locked = 1, current_level = ?, review_stage = ? WHERE id = ?',
                ('college_failed', 'college', 'college', project_id)
            )
            conn.execute(
                '''
                INSERT INTO project_node_status (project_id, node_name, current_status, comment, award_level, updated_by, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(project_id, node_name) DO UPDATE SET
                    current_status=excluded.current_status,
                    updated_by=excluded.updated_by,
                    updated_at=CURRENT_TIMESTAMP
                ''',
                (project_id, '学院赛', '未推荐', '', '', user_id)
            )
            try:
                conn.execute(
                    "UPDATE project_node_status SET current_status = '' WHERE project_id = ? AND node_name IN ('校赛','省赛','国赛')",
                    (project_id,)
                )
            except Exception:
                pass
        if template_name == '大挑' and updates.get('school_review_result') == 'rejected':
            conn.execute(
                'UPDATE projects SET status = ?, school_result_locked = 1, current_level = ?, review_stage = ? WHERE id = ?',
                ('school_failed', 'school', 'school', project_id)
            )
            conn.execute(
                '''
                INSERT INTO project_node_status (project_id, node_name, current_status, comment, award_level, updated_by, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(project_id, node_name) DO UPDATE SET
                    current_status=excluded.current_status,
                    updated_by=excluded.updated_by,
                    updated_at=CURRENT_TIMESTAMP
                ''',
                (project_id, '校赛', '未推荐', '', '', user_id)
            )
            try:
                conn.execute(
                    "UPDATE project_node_status SET current_status = '' WHERE project_id = ? AND node_name IN ('省赛','国赛')",
                    (project_id,)
                )
            except Exception:
                pass
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
    if template_name not in ['大挑', '国创赛', '小挑', '三创赛常规赛', '三创赛实战赛']:
        return fail('该项目类型不支持录入省赛/国赛结果', 400)

    prov_status = (data.get('provincial_status') or '').strip()
    nat_status = (data.get('national_status') or '').strip()
    allowed_status = {'未参赛', '已参赛', '已获奖'}
    if prov_status and prov_status not in allowed_status:
        return fail('省赛状态无效', 400)
    if nat_status and nat_status not in allowed_status:
        return fail('国赛状态无效', 400)

    prov_award = normalize_award_level(data.get('provincial_award_level'))
    # 移除硬编码校验，由 normalize_award_level 统一处理并允许自定义输入
    
    nat_award = normalize_award_level(data.get('national_award_level'))

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
                prov_award if prov_award is not None else (project['provincial_award_level'] or 'none'),
                prov_cert,
                advance_national,
                prov_comment,
                nat_status,
                nat_award if nat_award is not None else (project['national_award_level'] or 'none'),
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

        if nat_status == '已获奖' and nat_award != 'none':
            conn.execute(
                'UPDATE projects SET national_award_level = ?, status = ?, level = ? WHERE id = ?',
                (nat_award or '已获奖', 'finished_national_award', '国赛获奖', project_id)
            )
            conn.execute(
                'INSERT OR REPLACE INTO project_node_status (project_id, node_name, current_status, comment, award_level, updated_by, updated_at) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)',
                (project_id, '国赛', '已获奖', nat_comment, nat_award or '已获奖', user_id)
            )
        elif nat_status == '已参赛':
            conn.execute(
                'INSERT OR IGNORE INTO project_node_status (project_id, node_name, current_status, comment, award_level, updated_by, updated_at) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)',
                (project_id, '国赛', '待评审', '', '', user_id)
            )

        try:
            create_project_related_notifications(
                conn,
                project_id,
                '省赛/国赛结果更新',
                f'项目《{project["title"]}》省赛/国赛结果已更新。',
                exclude_user_id=user_id,
                include_advisor=False
            )
        except Exception:
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
    role = session.get('role')
    data = request.json or {}
    stage = normalize_review_stage(data.get('stage'))
    award_level = normalize_award_level(data.get('award_level'))
    recommend_flag = 1 if data.get('recommend_to_national') else 0
    eligible_recommend = (stage == 'provincial' and award_level in ['special', 'first', 'gold'])

    if stage not in ['school', 'provincial', 'national']:
        return fail('赛事阶段无效', 400)
    if not award_level:
        return fail('获奖等级为必填项', 400)
    if len(award_level) > 50:
        return fail('获奖等级过长', 400)

    if recommend_flag:
        if role not in [ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN']]:
            return fail('无权限操作“是否推荐至国赛”', 403)
        if not eligible_recommend:
            return fail('当前阶段/获奖等级不支持推荐至国赛', 400)

    conn = get_db_connection()
    project = conn.execute('SELECT id, title, created_by FROM projects WHERE id = ?', (project_id,)).fetchone()
    if not project:
        return fail('项目不存在', 404)

    try:
        cur = conn.execute(
            '''
            INSERT INTO project_awards (project_id, stage, award_level, award_name, award_time, issuer, recommend_national, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                project_id,
                stage,
                award_level,
                (data.get('award_name') or '').strip(),
                (data.get('award_time') or '').strip(),
                (data.get('issuer') or '').strip(),
                1 if recommend_flag else 0,
                user_id
            )
        )
        award_id = None
        try:
            award_id = int(cur.lastrowid) if cur and cur.lastrowid is not None else None
        except Exception:
            award_id = None
        new_row = None
        if award_id:
            try:
                new_row = conn.execute('SELECT * FROM project_awards WHERE id = ?', (award_id,)).fetchone()
            except Exception:
                new_row = None
        sync_award_to_project_results(conn, project_id, stage, award_level, user_id, recommend_national=(1 if recommend_flag else 0))
        if recommend_flag:
            try:
                title_txt = str(project['title'] or '').strip() or f'项目#{project_id}'
                create_notification(
                    conn,
                    project['created_by'],
                    '已推荐至国赛',
                    f'项目《{title_txt}》已推荐至国赛，国赛阶段已解锁。',
                    'project',
                    meta={'route': f'/project/{int(project_id)}', 'project_id': int(project_id)}
                )
                try:
                    p2 = conn.execute('SELECT advisor_name FROM projects WHERE id = ?', (project_id,)).fetchone()
                    adv = (p2['advisor_name'] if p2 else '') or ''
                    for tid in resolve_teacher_user_ids(conn, adv):
                        create_notification(
                            conn,
                            tid,
                            '已推荐至国赛',
                            f'项目《{title_txt}》已推荐至国赛，国赛阶段已解锁。',
                            'project',
                            meta={'route': f'/project/{int(project_id)}', 'project_id': int(project_id)}
                        )
                except Exception:
                    pass
            except Exception:
                pass
        try:
            stage_txt = '校赛' if stage == 'school' else ('省赛' if stage == 'provincial' else ('国赛' if stage == 'national' else stage))
            level_txt = award_level_code_to_label(award_level) or award_level
            name_txt = (data.get('award_name') or '').strip()
            time_txt = (data.get('award_time') or '').strip()
            issuer_txt = (data.get('issuer') or '').strip()
            parts = [f'项目《{project["title"]}》新增获奖记录']
            if stage_txt:
                parts.append(f'阶段：{stage_txt}')
            if level_txt and level_txt != 'none':
                parts.append(f'等级：{level_txt}')
            if recommend_flag:
                parts.append('已推荐至国赛')
            if name_txt:
                parts.append(f'奖项名称：{name_txt}')
            if time_txt:
                parts.append(f'获奖时间：{time_txt}')
            if issuer_txt:
                parts.append(f'颁奖单位：{issuer_txt}')
            create_project_related_notifications(
                conn,
                project_id,
                '获奖记录更新',
                '；'.join([p for p in parts if p]),
                exclude_user_id=user_id,
                include_advisor=False
            )
        except Exception:
            create_notification(conn, project['created_by'], '获奖记录更新', f'项目《{project["title"]}》新增获奖记录（{stage}）', 'system')
        log_action(conn, user_id, 'AWARD_CREATE', f'Project {project_id} stage={stage} level={award_level}', request.remote_addr)
        conn.commit()
        return success(data=(dict(new_row) if new_row else None), message='已新增获奖记录')
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
    role = session.get('role')
    data = request.json or {}
    stage = normalize_review_stage(data.get('stage'))
    award_level = normalize_award_level(data.get('award_level'))
    recommend_in_payload = ('recommend_to_national' in data)
    recommend_flag = 1 if data.get('recommend_to_national') else 0
    eligible_recommend = (stage == 'provincial' and award_level in ['special', 'first', 'gold'])

    if stage not in ['school', 'provincial', 'national']:
        return fail('赛事阶段无效', 400)
    if not award_level:
        return fail('获奖等级为必填项', 400)
    if len(award_level) > 50:
        return fail('获奖等级过长', 400)

    conn = get_db_connection()
    row = conn.execute('SELECT * FROM project_awards WHERE id = ?', (award_id,)).fetchone()
    if not row:
        return fail('获奖记录不存在', 404)

    try:
        old_rec = 1 if int(row['recommend_national'] or 0) == 1 else 0
    except Exception:
        old_rec = 0
    if recommend_in_payload and recommend_flag != old_rec:
        if role not in [ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN']]:
            return fail('无权限操作“是否推荐至国赛”', 403)
        if recommend_flag and not eligible_recommend:
            return fail('当前阶段/获奖等级不支持推荐至国赛', 400)

    try:
        conn.execute(
            '''
            UPDATE project_awards
            SET stage = ?, award_level = ?, award_name = ?, award_time = ?, issuer = ?, recommend_national = ?
            WHERE id = ?
            ''',
            (
                stage,
                award_level,
                (data.get('award_name') or '').strip(),
                (data.get('award_time') or '').strip(),
                (data.get('issuer') or '').strip(),
                (1 if recommend_flag else 0) if recommend_in_payload else (old_rec),
                award_id
            )
        )
        sync_award_to_project_results(
            conn,
            row['project_id'],
            stage,
            award_level,
            user_id,
            recommend_national=((1 if recommend_flag else 0) if recommend_in_payload else old_rec)
        )
        updated_row = None
        try:
            updated_row = conn.execute('SELECT * FROM project_awards WHERE id = ?', (award_id,)).fetchone()
        except Exception:
            updated_row = None
        if recommend_in_payload and (recommend_flag != old_rec):
            if recommend_flag:
                try:
                    p = conn.execute('SELECT title, created_by, advisor_name FROM projects WHERE id = ?', (row['project_id'],)).fetchone()
                    title_txt = str((p['title'] if p else '') or '').strip() or f'项目#{row["project_id"]}'
                    if p and p['created_by']:
                        create_notification(
                            conn,
                            p['created_by'],
                            '已推荐至国赛',
                            f'项目《{title_txt}》已推荐至国赛，国赛阶段已解锁。',
                            'project',
                            meta={'route': f'/project/{int(row["project_id"])}', 'project_id': int(row['project_id'])}
                        )
                    adv = (p['advisor_name'] if p else '') or ''
                    for tid in resolve_teacher_user_ids(conn, adv):
                        create_notification(
                            conn,
                            tid,
                            '已推荐至国赛',
                            f'项目《{title_txt}》已推荐至国赛，国赛阶段已解锁。',
                            'project',
                            meta={'route': f'/project/{int(row["project_id"])}', 'project_id': int(row['project_id'])}
                        )
                except Exception:
                    pass
        try:
            p = conn.execute('SELECT title FROM projects WHERE id = ?', (row['project_id'],)).fetchone()
            p_title = (p['title'] if p else '') or str(row['project_id'])
            stage_txt = '校赛' if stage == 'school' else ('省赛' if stage == 'provincial' else ('国赛' if stage == 'national' else stage))
            level_txt = award_level_code_to_label(award_level) or award_level
            name_txt = (data.get('award_name') or '').strip()
            time_txt = (data.get('award_time') or '').strip()
            issuer_txt = (data.get('issuer') or '').strip()
            parts = [f'项目《{p_title}》获奖记录已更新']
            if stage_txt:
                parts.append(f'阶段：{stage_txt}')
            if level_txt and level_txt != 'none':
                parts.append(f'等级：{level_txt}')
            if (recommend_in_payload and recommend_flag) or ((not recommend_in_payload) and old_rec):
                parts.append('已推荐至国赛')
            if name_txt:
                parts.append(f'奖项名称：{name_txt}')
            if time_txt:
                parts.append(f'获奖时间：{time_txt}')
            if issuer_txt:
                parts.append(f'颁奖单位：{issuer_txt}')
            create_project_related_notifications(
                conn,
                row['project_id'],
                '获奖记录更新',
                '；'.join([p for p in parts if p]),
                exclude_user_id=user_id,
                include_advisor=False
            )
        except Exception:
            pass
        log_action(conn, user_id, 'AWARD_UPDATE', f'Award {award_id}', request.remote_addr)
        conn.commit()
        return success(data=(dict(updated_row) if updated_row else None), message='已更新获奖记录')
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

@projects_bp.route('/projects/upgrades', methods=['POST'])
@login_required
def route_request_project_upgrade():
    from .upgrade_views import request_project_upgrade
    return request_project_upgrade()

@projects_bp.route('/projects/upgrades/pending', methods=['GET'])
@login_required
def route_get_pending_upgrades():
    from .upgrade_views import get_pending_upgrades
    return get_pending_upgrades()

@projects_bp.route('/projects/upgrades/<int:upgrade_id>/audit', methods=['POST'])
@login_required
def route_audit_project_upgrade(upgrade_id):
    from .upgrade_views import audit_project_upgrade
    return audit_project_upgrade(upgrade_id)

@projects_bp.route('/projects/<int:project_id>/upgrades/history', methods=['GET'])
@login_required
def route_get_upgrade_history(project_id):
    from .upgrade_views import get_upgrade_history
    return get_upgrade_history(project_id)


# ------------------------------
# Legacy library (经验库) APIs
# ------------------------------

def legacy_category_from_template(template_name: str | None):
    """
    经验库分类：创新类 (大挑, 大创创新), 创业类 (国创赛, 小挑, 三创赛, 大创创业)
    """
    if not template_name:
        return 'entrepreneurship'
    if template_name in ['大挑', '大创创新训练']:
        return 'innovation'
    return 'entrepreneurship'

def legacy_competition_type_from_template(template_name: str | None, project_type: str | None = None, project_category: str | None = None):
    tpl = (template_name or '').strip()
    mapping = {
        '大挑': 'challenge_cup',
        '国创赛': 'internet_plus',
        '小挑': 'youth_challenge',
        '三创赛常规赛': 'three_creativity_regular',
        '三创赛实战赛': 'three_creativity_practical',
        '大创创新训练': 'innovation',
        '大创创业训练': 'entrepreneurship_training',
        '大创创业实践': 'entrepreneurship_practice'
    }
    if tpl in mapping:
        return mapping[tpl]
    p_type = (project_type or '').strip()
    if p_type in ['innovation', 'entrepreneurship_training', 'entrepreneurship_practice', 'challenge_cup', 'internet_plus', 'youth_challenge', 'three_creativity_regular', 'three_creativity_practical']:
        return p_type
    cat = (project_category or '').strip()
    if cat == 'entrepreneurship':
        return 'entrepreneurship_training'
    return 'innovation'

def normalize_final_grade(v):
    s = (v or '').strip().lower()
    if s in ['excellent', '优秀']:
        return '优秀'
    if s in ['good', '良好']:
        return '良好'
    if s in ['pass', 'qualified', '合格']:
        return '合格'
    if s in ['fail', 'unqualified', '不合格']:
        return '不合格'
    return (v or '').strip()

def is_experience_eligible(project_row, extra_info, template_name: str | None):
    tpl = (template_name or '').strip()
    info = extra_info if isinstance(extra_info, dict) else {}
    if tpl in ['大挑', '国创赛', '小挑', '三创赛常规赛', '三创赛实战赛']:
        status = str((project_row or {}).get('status') or '').strip()
        if status not in ['rated', 'finished', 'finished_national_award']:
            return False
    if tpl == '大学生创新创业训练计划':
        p_type = str((project_row or {}).get('project_type') or '').strip()
        if p_type == 'innovation':
            status = str((project_row or {}).get('status') or '').strip()
            if status not in ['rated', 'finished', 'finished_national_award']:
                return False
        return normalize_final_grade(info.get('final_grade')) == '优秀'
    if tpl == '大创创新训练':
        status = str((project_row or {}).get('status') or '').strip()
        if status not in ['rated', 'finished', 'finished_national_award']:
            return False
        return normalize_final_grade(info.get('final_grade')) == '优秀'
    if tpl in ['大创创业训练', '大创创业实践']:
        return normalize_final_grade(info.get('final_grade')) == '优秀'
    al = normalize_award_level(get_award_level_for_project(project_row))
    return al in ['gold', 'silver', 'bronze', 'special', 'first', 'second', 'third', 'excellent']

def is_legacy_collection_ready(project_row, extra_info, template_name: str | None):
    status = str((project_row or {}).get('status') or '').strip()
    if status not in ['rated', 'finished', 'finished_national_award']:
        return False
    return is_experience_eligible(project_row, extra_info, template_name)


def sanitize_sensitive_public_text(text: str | None):
    """
    创业类经验库：只允许存储“公开可描述”的内容。对疑似商业机密触发脱敏。
    """
    s = (text or '').strip()
    if not s:
        return ''
    # 常见商业机密关键词（覆盖财务/客户/核心技术等）
    sensitive_patterns = [
        r'客户', r'收入', r'利润', r'资金', r'融资', r'投资', r'订单', r'合同', r'发票',
        r'专利', r'算法', r'核心技术', r'研发', r'数据库', r'服务器', r'技术路线', r'模型参数'
    ]
    for pat in sensitive_patterns:
        if re.search(pat, s, flags=re.IGNORECASE):
            return '[已脱敏]'
    return s


def redact_personal_info(text: str | None, tokens: list[str]):
    """
    创新类专家评语脱敏：去掉人名、单位（简化实现：对已知 tokens 进行替换）。
    """
    s = (text or '').strip()
    if not s:
        return ''
    for t in tokens:
        if t:
            s = s.replace(t, '')
    # 去掉多余空格/标点重复
    s = re.sub(r'\s+', ' ', s).strip()
    s = s.replace('，，', '，').replace('..', '.')
    return s


def get_award_level_for_project(project_row):
    """
    经验库展示：获奖等级。
    """
    nat = (project_row.get('national_award_level') or '').strip() if project_row else ''
    prov = (project_row.get('provincial_award_level') or '').strip() if project_row else ''
    if nat and nat != 'none':
        return nat
    if prov and prov != 'none':
        return prov
    return ''

def get_review_task_comments_for_project(conn, project_id):
    rows = conn.execute(
        '''
        SELECT t.review_level, t.comments, t.score_details, u.real_name, u.college, u.department
        FROM review_tasks t
        LEFT JOIN users u ON t.judge_id = u.id
        WHERE t.project_id = ? AND t.status = 'completed'
          AND t.review_level IN ('college', 'school')
        ORDER BY t.review_level, t.id
        ''',
        (project_id,)
    ).fetchall()
    parts = []
    for r in rows:
        c = (r['comments'] or '').strip()
        if not c:
            try:
                details = json.loads(r['score_details'] or '{}')
            except Exception:
                details = {}
            reasons = []
            if isinstance(details, dict):
                for _, item in details.items():
                    if not isinstance(item, dict):
                        continue
                    reason = sanitize_public_text(item.get('reason'))
                    if reason:
                        reasons.append(reason)
            c = '；'.join(reasons).strip()
        if not c:
            continue
        tokens = [(r['real_name'] or '').strip(), (r['college'] or '').strip(), (r['department'] or '').strip()]
        parts.append(redact_personal_info(c, [t for t in tokens if t]))
    return sanitize_public_text('\n'.join(parts))

def sanitize_public_text(text):
    s = (text or '').strip()
    if not s:
        return ''
    s = re.sub(r'(?i)[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}', '***@***', s)
    s = re.sub(r'(?<!\d)1\d{10}(?!\d)', '***********', s)
    s = re.sub(r'(?<!\d)\d{17}[\dXx](?!\d)', '******************', s)
    s = re.sub(r'(?<!\d)\d{6,12}(?!\d)', '********', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def sanitize_rich_html(html):
    s = (html or '').strip()
    if not s:
        return ''
    s = re.sub(r'(?is)<(script|style|iframe|object|embed)[^>]*>.*?</\1>', '', s)
    s = re.sub(r'(?is)<(script|style|iframe|object|embed)[^>]*/>', '', s)
    s = re.sub(r'(?i)\son\w+\s*=\s*\"[^\"]*\"', '', s)
    s = re.sub(r"(?i)\son\w+\s*=\s*'[^']*'", '', s)
    s = re.sub(r'(?i)\son\w+\s*=\s*[^\s>]+', '', s)
    s = re.sub(r'(?i)javascript:', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def strip_html(html):
    s = re.sub(r'(?is)<[^>]+>', ' ', str(html or ''))
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def mask_name(name):
    s = (name or '').strip()
    if not s:
        return ''
    if len(s) == 1:
        return '*'
    if len(s) == 2:
        return s[0] + '*'
    return s[0] + '*' * (len(s) - 2) + s[-1]

def award_level_label(code):
    s = (code or '').strip().lower()
    if s == 'gold':
        return '金奖'
    if s == 'silver':
        return '银奖'
    if s == 'bronze':
        return '铜奖'
    if s == 'special':
        return '特等奖'
    if s == 'first':
        return '一等奖'
    if s == 'second':
        return '二等奖'
    if s == 'third':
        return '三等奖'
    if s == 'excellent':
        return '优秀奖'
    if s in ['优秀', '良好', '合格', '不合格']:
        return code
    if s == 'none':
        return ''
    return code or ''

def can_manage_legacy(role):
    return role == ROLES['SCHOOL_APPROVER']

def can_bypass_legacy_declaration(role):
    return role in [ROLES['SCHOOL_APPROVER'], ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN']]

def can_access_legacy_library(conn, user_id, role):
    if can_manage_legacy(role) or role in [ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN']]:
        return True
    if role not in [ROLES['STUDENT'], ROLES['TEACHER']]:
        return False
    u = conn.execute('SELECT status, real_name, identity_number FROM users WHERE id = ?', (user_id,)).fetchone()
    if not u:
        return False
    if str(u['status'] or '').strip() != 'active':
        return False
    if not str(u['real_name'] or '').strip():
        return False
    if role == ROLES['STUDENT'] and not str(u['identity_number'] or '').strip():
        return False
    return True

def get_user_legacy_unlock_status(conn, legacy_id, user_id):
    borrowed = conn.execute(
        'SELECT 1 FROM project_borrow_records WHERE legacy_id = ? AND user_id = ?',
        (legacy_id, user_id)
    ).fetchone()
    if borrowed:
        return {'unlocked': True, 'mode': 'instant', 'request_status': None}

    req = conn.execute(
        '''
        SELECT status FROM legacy_borrow_requests
        WHERE legacy_id = ? AND user_id = ?
        ORDER BY created_at DESC, id DESC LIMIT 1
        ''',
        (legacy_id, user_id)
    ).fetchone()
    if not req:
        return {'unlocked': False, 'mode': 'apply', 'request_status': None}
    st = str(req['status'] or '').strip()
    return {'unlocked': st == 'approved', 'mode': 'apply', 'request_status': st}


@projects_bp.route('/legacy', methods=['GET', 'POST'])
@login_required
def legacy_library():
    """
    GET：学生端/管理员端查看经验库（支持分类与搜索）
    POST：收录至经验库（创新类自动收录或询问；创业类管理员手动收录）
    """
    conn = get_db_connection()
    try:
        user_id = session.get('user_id')
        role = session.get('role')

        if request.method == 'GET':
            keyword = (request.args.get('keyword') or '').strip()
            category = (request.args.get('category') or 'all').strip().lower()
            competition_type_filter = (request.args.get('competition_type') or 'all').strip()
            award_level = (request.args.get('award_level') or 'all').strip()
            status = (request.args.get('status') or '').strip()
            only_borrowed = request.args.get('only_borrowed') == '1'

            is_student = (role == ROLES['STUDENT'])
            is_teacher = (role == ROLES['TEACHER'])
            if not can_access_legacy_library(conn, user_id, role):
                return fail('仅校内实名认证师生可访问经验库', 403)
            
            teacher_name = ''
            if is_teacher:
                tu = conn.execute('SELECT real_name FROM users WHERE id = ?', (user_id,)).fetchone()
                teacher_name = str((tu['real_name'] if tu else '') or '').strip()
            teacher_pending_mode = bool(is_teacher and status == 'pending_teacher' and teacher_name)

            base_query = "SELECT l.* FROM project_legacy l WHERE 1=1"
            params = []
            if teacher_pending_mode:
                base_query = "SELECT l.*, p.status AS _project_status, p.national_award_level AS _nat_award_level, p.provincial_award_level AS _prov_award_level FROM project_legacy l JOIN projects p ON p.id = l.original_project_id WHERE l.status = 'pending_teacher' AND p.advisor_name = ?"
                params.append(teacher_name)
            elif not can_bypass_legacy_declaration(role):
                base_query += " AND l.status = 'approved'"
            
            if keyword:
                base_query += " AND (l.title LIKE ? OR l.project_summary LIKE ? OR l.methodology_summary LIKE ? OR l.expert_comments LIKE ? OR l.industry_field LIKE ? OR l.team_experience LIKE ? OR l.pitfalls LIKE ?)"
                like = f"%{keyword}%"
                params.extend([like] * 7)

            if category != 'all':
                base_query += " AND l.project_category = ?"
                params.append(category)

            if status and can_manage_legacy(role):
                base_query += " AND l.status = ?"
                params.append(status)

            if award_level and award_level != 'all':
                base_query += " AND l.award_level = ?"
                params.append(award_level)

            if base_query.startswith("SELECT l.* FROM project_legacy l"):
                base_query = base_query.replace(
                    "SELECT l.* FROM project_legacy l",
                    "SELECT l.*, p.status AS _project_status, p.national_award_level AS _nat_award_level, p.provincial_award_level AS _prov_award_level FROM project_legacy l LEFT JOIN projects p ON p.id = l.original_project_id",
                    1
                )
            base_query += " ORDER BY l.created_at DESC"
            rows = conn.execute(base_query, params).fetchall()

            result = []
            pending_filter = bool(status in ['pending', 'pending_school', 'pending_teacher'] and (can_manage_legacy(role) or teacher_pending_mode))
            for r in rows:
                if pending_filter:
                    try:
                        p_row = conn.execute(
                            '''
                            SELECT p.*, c.template_type AS competition_template_type, c.title AS competition_title
                            FROM projects p
                            LEFT JOIN competitions c ON p.competition_id = c.id
                            WHERE p.id = ?
                            ''',
                            (r['original_project_id'],)
                        ).fetchone()
                        if not p_row:
                            continue
                        project = dict(p_row)
                        resolved_template = resolve_template_name(project)
                        try:
                            p_info = json.loads(project.get('extra_info') or '{}')
                        except Exception:
                            p_info = {}
                        if not is_legacy_collection_ready(project, p_info, resolved_template):
                            continue
                    except Exception:
                        continue
                row = dict(r)
                p_status = str(row.get('_project_status') or '').strip()
                if (not teacher_pending_mode) and (not can_bypass_legacy_declaration(role)) and p_status and p_status not in ['rated', 'finished', 'finished_national_award']:
                    continue
                nat_lv = str(row.get('_nat_award_level') or '').strip()
                prov_lv = str(row.get('_prov_award_level') or '').strip()
                stage = 'national' if nat_lv and nat_lv != 'none' else ('provincial' if prov_lv and prov_lv != 'none' else '')
                stage_label = '国赛' if stage == 'national' else ('省赛' if stage == 'provincial' else '')
                row['methodology_summary'] = sanitize_public_text(row.get('methodology_summary'))
                row['project_summary'] = sanitize_public_text(row.get('project_summary'))
                row['expert_comments'] = sanitize_public_text(row.get('expert_comments'))
                row['industry_field'] = sanitize_public_text(row.get('industry_field'))
                row['team_experience'] = sanitize_public_text(row.get('team_experience'))
                row['pitfalls'] = sanitize_public_text(row.get('pitfalls'))
                row['business_model_overview'] = sanitize_public_text(row.get('business_model_overview'))
                row['award_level_label'] = award_level_label(row.get('award_level'))
                award_text = str(row.get('award_level_label') or '').strip()
                if stage_label and award_text:
                    row['award_level_display'] = f'{stage_label}·{award_text}'
                else:
                    row['award_level_display'] = award_text
                row['award_stage'] = stage
                row['award_stage_label'] = stage_label
                row.pop('_project_status', None)
                row.pop('_nat_award_level', None)
                row.pop('_prov_award_level', None)
                row['competition_type'] = legacy_competition_type_from_template(
                    row.get('template_name'),
                    row.get('project_type'),
                    row.get('project_category')
                )
                if competition_type_filter and competition_type_filter != 'all' and row['competition_type'] != competition_type_filter:
                    continue
                is_public = int(row.get('is_public') or 0) == 1
                row['borrow_mode'] = 'instant' if is_public else 'apply'
                if can_bypass_legacy_declaration(role):
                    row['is_borrowed'] = True
                    row['borrow_request_status'] = None
                else:
                    if is_teacher:
                        row['is_borrowed'] = True
                        row['borrow_request_status'] = None
                    else:
                        unlock = get_user_legacy_unlock_status(conn, row['id'], user_id)
                        row['is_borrowed'] = bool(unlock.get('unlocked'))
                        row['borrow_request_status'] = unlock.get('request_status')

                if only_borrowed and not row.get('is_borrowed'):
                    continue

                if not can_bypass_legacy_declaration(role) and not row.get('is_borrowed'):
                    for k in ['methodology_summary', 'project_summary', 'expert_comments', 'industry_field', 'team_experience', 'pitfalls', 'business_model_overview', 'ppt_url', 'experience_sections']:
                        if k in row:
                            row[k] = ''
                result.append(row)

            return success(data=result)

        # POST
        data = request.json or {}
        original_project_id = data.get('original_project_id')
        
        if not original_project_id:
            return fail('参数 original_project_id 缺失', 400)
        
        project_row = conn.execute(
            '''
            SELECT p.*, c.template_type AS competition_template_type, c.title AS competition_title
            FROM projects p
            LEFT JOIN competitions c ON p.competition_id = c.id
            WHERE p.id = ?
            ''',
            (original_project_id,)
        ).fetchone()
        if not project_row:
            return fail('原项目不存在', 404)
        project = dict(project_row)

        # 确定分类
        resolved_template = resolve_template_name(project)
        if (resolved_template or '').strip() == '大学生创新创业训练计划':
            derived_category = 'innovation' if (project.get('project_type') or '') == 'innovation' else 'entrepreneurship'
        else:
            derived_category = legacy_category_from_template(resolved_template)
        legacy_competition_type = legacy_competition_type_from_template(
            resolved_template,
            project.get('project_type'),
            derived_category
        )

        try:
            project_info = json.loads(project.get('extra_info') or '{}')
        except Exception:
            project_info = {}
        if role == ROLES['STUDENT'] and int(project.get('created_by') or 0) != int(user_id or 0):
            return fail('无权限', 403)
        if not is_legacy_collection_ready(project, project_info, resolved_template):
            return fail('当前项目未结题或不符合经验提交流程（需结题且优秀/获奖项目）', 400)

        if resolved_template in ['大创创新训练', '大学生创新创业训练计划']:
            if role != ROLES['STUDENT'] or int(project.get('created_by') or 0) != int(user_id or 0):
                return fail('仅项目负责人可提交经验内容', 403)
        else:
            if role not in [ROLES['STUDENT'], ROLES['TEACHER'], ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN']]:
                return fail('无权限', 403)
        is_public = 0

        # 提取字段
        title = (data.get('title') or project.get('title') or '').strip()
        award_level = get_award_level_for_project(project)
        experience_sections = ''
        try:
            if isinstance(project_info.get('methodology_sections'), dict):
                experience_sections = json.dumps(project_info.get('methodology_sections') or {}, ensure_ascii=False)
        except Exception:
            experience_sections = ''
        project_summary = (data.get('project_summary') or project.get('abstract') or '').strip()
        methodology_summary = (data.get('methodology_summary') or project_info.get('methodology_summary') or '').strip()
        
        # 创新类专家评语脱敏
        expert_comments = ''
        expert_comments = get_review_task_comments_for_project(conn, original_project_id)
        
        # 创业类字段（管理员手动脱敏）
        industry_field = (data.get('industry_field') or '').strip()
        team_experience = (data.get('team_experience') or '').strip()
        pitfalls = (data.get('pitfalls') or data.get('avoidance_guide') or '').strip()
        
        # 检查是否已存在
        existing = conn.execute(
            'SELECT id FROM project_legacy WHERE original_project_id = ? AND project_category = ?',
            (original_project_id, derived_category)
        ).fetchone()

        if existing:
            conn.execute('''
                UPDATE project_legacy
                SET title = ?, project_summary = ?, methodology_summary = ?, expert_comments = ?,
                    industry_field = ?, team_experience = ?, pitfalls = ?, is_public = ?,
                    status = ?, submitted_by = ?, reviewed_by = NULL, reviewed_at = NULL, reject_reason = NULL
                WHERE id = ?
            ''', (
                sanitize_public_text(title),
                sanitize_public_text(project_summary),
                sanitize_public_text(methodology_summary),
                sanitize_public_text(expert_comments),
                sanitize_public_text(industry_field),
                sanitize_public_text(team_experience),
                sanitize_public_text(pitfalls),
                is_public,
                'pending',
                user_id,
                existing['id']
            ))
            try:
                conn.execute(
                    'UPDATE project_legacy SET template_name = ?, experience_sections = ? WHERE id = ?',
                    (resolved_template, experience_sections, existing['id'])
                )
            except Exception:
                pass
        else:
            conn.execute('''
                INSERT INTO project_legacy (
                    original_project_id, project_category, project_type, award_level, 
                    title, project_summary, methodology_summary, expert_comments, industry_field, 
                    team_experience, pitfalls, is_public, status, submitted_by, template_name, experience_sections
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                original_project_id, derived_category, legacy_competition_type, award_level,
                sanitize_public_text(title),
                sanitize_public_text(project_summary),
                sanitize_public_text(methodology_summary),
                sanitize_public_text(expert_comments),
                sanitize_public_text(industry_field),
                sanitize_public_text(team_experience),
                sanitize_public_text(pitfalls),
                is_public,
                'pending',
                user_id,
                resolved_template,
                experience_sections
            ))
        
        # 标记原项目已收录
        try:
            extra_info = json.loads(project.get('extra_info') or '{}')
        except:
            extra_info = {}
        extra_info['legacy_prompted'] = True
        conn.execute('UPDATE projects SET extra_info = ? WHERE id = ?', (json.dumps(extra_info), original_project_id))
        
        # 国赛获奖并收录经验库后，项目状态显示为 “已结项·国赛获奖”
        if project.get('status') == 'finished_national_award' or (project.get('national_award_level') and project.get('national_award_level') != 'none'):
            conn.execute('UPDATE projects SET status = ? WHERE id = ?', ('finished_national_award', original_project_id))

        conn.commit()
        return success(message='已提交入库审核')

    except Exception as e:
        conn.rollback()
        return fail(str(e), 500)
    finally:
        conn.close()


@projects_bp.route('/legacy/<int:legacy_id>/borrow', methods=['POST'])
@login_required
def borrow_legacy(legacy_id):
    """
    借鉴此项目思路：系统记录次数，申报时可引用
    """
    role = session.get('role')
    conn = get_db_connection()
    user_id = session.get('user_id')
    try:
        if not can_access_legacy_library(conn, user_id, role):
            return fail('仅校内实名认证师生可进行借鉴', 403)
        if role not in [ROLES['STUDENT'], ROLES['TEACHER']]:
            return fail('无权限借鉴', 403)

        legacy = conn.execute('SELECT id, is_public, status FROM project_legacy WHERE id = ?', (legacy_id,)).fetchone()
        if not legacy:
            return fail('经验库项目不存在', 404)
        if int(legacy['is_public'] or 0) != 1 or (legacy['status'] or '') != 'approved':
            return fail('该经验库项目未公开', 403)
            
        data = request.json or {}
        agreement_version = sanitize_public_text(data.get('agreement_version') or 'v1')
        agreement_text = sanitize_public_text(data.get('agreement_text') or '')
        reason = sanitize_public_text(data.get('reason') or '')
        if reason and len(reason) > 500:
            return fail('备注过长', 400)
            
        # 检查是否已借鉴
        existing = conn.execute(
            'SELECT id FROM project_borrow_records WHERE legacy_id = ? AND user_id = ?',
            (legacy_id, user_id)
        ).fetchone()
        
        if existing:
            cnt = conn.execute('SELECT borrowed_count FROM project_legacy WHERE id = ?', (legacy_id,)).fetchone()['borrowed_count']
            return success(data={'borrowed_count': cnt, 'already_borrowed': True}, message='已解锁，无需重复确认')

        if role == ROLES['TEACHER']:
            cnt = conn.execute('SELECT borrowed_count FROM project_legacy WHERE id = ?', (legacy_id,)).fetchone()['borrowed_count']
            return success(data={'borrowed_count': cnt, 'already_borrowed': True}, message='导师访问无需承诺，已具备查看/下载权限')
            
        conn.execute(
            'INSERT INTO project_borrow_records (legacy_id, user_id, reason) VALUES (?, ?, ?)',
            (legacy_id, user_id, json.dumps({'agreement_version': agreement_version, 'agreement_text': agreement_text, 'reason': reason}, ensure_ascii=False))
        )
        conn.execute(
            'UPDATE project_legacy SET borrowed_count = borrowed_count + 1 WHERE id = ?',
            (legacy_id,)
        )
        log_action(conn, user_id, 'LEGACY_BORROW', json.dumps({'legacy_id': legacy_id, 'agreement_version': agreement_version}, ensure_ascii=False), request.remote_addr)
        conn.commit()
        
        # 获取最新次数
        cnt = conn.execute('SELECT borrowed_count FROM project_legacy WHERE id = ?', (legacy_id,)).fetchone()['borrowed_count']
        
        return success(data={'borrowed_count': cnt, 'already_borrowed': False}, message='借鉴成功，已永久解锁查看/下载权限')
    except Exception as e:
        conn.rollback()
        return fail(str(e), 500)
    finally:
        conn.close()


@projects_bp.route('/legacy/borrow', methods=['POST'])
@login_required
def borrow_legacy_compat():
    data = request.json or {}
    legacy_id = data.get('legacy_id')
    if not legacy_id:
        return fail('参数 legacy_id 缺失', 400)
    return borrow_legacy(int(legacy_id))


@projects_bp.route('/legacy/<int:legacy_id>/apply-borrow', methods=['POST'])
@login_required
def apply_borrow_legacy(legacy_id):
    role = session.get('role')
    user_id = session.get('user_id')
    conn = get_db_connection()
    try:
        if not can_access_legacy_library(conn, user_id, role):
            return fail('仅校内实名认证师生可申请借鉴', 403)
        if role not in [ROLES['STUDENT'], ROLES['TEACHER']]:
            return fail('无权限', 403)

        legacy = conn.execute('SELECT id, title, original_project_id, is_public, status FROM project_legacy WHERE id = ?', (legacy_id,)).fetchone()
        if not legacy:
            return fail('经验库项目不存在', 404)
        if (legacy['status'] or '') != 'approved':
            return fail('当前不可申请借鉴', 400)
        if int(legacy['is_public'] or 0) == 1:
            return fail('公开级项目无需申请，可直接借鉴解锁', 400)

        latest = conn.execute(
            '''
            SELECT id, status FROM legacy_borrow_requests
            WHERE legacy_id = ? AND user_id = ?
            ORDER BY created_at DESC, id DESC LIMIT 1
            ''',
            (legacy_id, user_id)
        ).fetchone()
        if latest and str(latest['status'] or '').strip() in ['pending_teacher', 'pending_college', 'pending_school', 'approved']:
            return success(data={'request_id': latest['id'], 'request_status': latest['status']}, message='申请已存在')

        data = request.json or {}
        reason = sanitize_public_text(data.get('reason') or '')
        if reason and len(reason) > 500:
            return fail('申请说明过长', 400)

        proj = None
        if legacy['original_project_id']:
            proj = conn.execute('SELECT id, title, advisor_name, college FROM projects WHERE id = ?', (legacy['original_project_id'],)).fetchone()
        if not proj:
            return fail('原项目不存在，无法申请', 400)
        advisor_name = str(proj['advisor_name'] or '').strip()
        if not advisor_name:
            return fail('原项目未绑定指导教师，无法申请', 400)
        advisor_ids = resolve_teacher_user_ids(conn, advisor_name)
        if not advisor_ids:
            return fail('未找到可审核的指导教师账号', 400)

        conn.execute(
            '''
            INSERT INTO legacy_borrow_requests (legacy_id, user_id, reason, status)
            VALUES (?, ?, ?, 'pending_teacher')
            ''',
            (legacy_id, user_id, reason)
        )
        req_id = conn.execute('SELECT last_insert_rowid() AS id').fetchone()['id']

        applicant = conn.execute('SELECT real_name, username FROM users WHERE id = ?', (user_id,)).fetchone()
        applicant_name = str((applicant['real_name'] if applicant else '') or (applicant['username'] if applicant else '') or '').strip()
        for tid in advisor_ids:
            create_notification(conn, tid, '待审核借鉴申请', f"用户 {applicant_name} 申请借鉴受控项目《{sanitize_public_text(legacy['title'])}》，请在系统中审核。", 'approval', meta={'route': '/legacy', 'legacy_id': int(legacy_id), 'request_id': int(req_id)})
        log_action(conn, user_id, 'LEGACY_BORROW_APPLY', json.dumps({'legacy_id': legacy_id, 'request_id': req_id}, ensure_ascii=False), request.remote_addr)
        conn.commit()
        return success(data={'request_id': req_id, 'request_status': 'pending_teacher'}, message='已提交申请，进入三级审核')
    except Exception as e:
        conn.rollback()
        return fail(str(e), 500)
    finally:
        conn.close()


@projects_bp.route('/legacy/borrow-requests', methods=['GET'])
@login_required
def list_legacy_borrow_requests():
    role = session.get('role')
    user_id = session.get('user_id')
    status = (request.args.get('status') or '').strip()
    conn = get_db_connection()
    try:
        if role not in [ROLES['TEACHER'], ROLES['COLLEGE_APPROVER'], ROLES['SCHOOL_APPROVER']]:
            return fail('无权限', 403)
        q = '''
            SELECT r.id, r.legacy_id, r.user_id, r.reason, r.status, r.created_at,
                   l.title AS legacy_title, l.original_project_id,
                   u.username AS applicant_username, u.real_name AS applicant_real_name,
                   p.advisor_name, p.college AS project_college
            FROM legacy_borrow_requests r
            JOIN project_legacy l ON r.legacy_id = l.id
            LEFT JOIN users u ON r.user_id = u.id
            LEFT JOIN projects p ON l.original_project_id = p.id
            WHERE 1=1
        '''
        params = []
        if role == ROLES['TEACHER']:
            teacher = conn.execute('SELECT real_name FROM users WHERE id = ?', (user_id,)).fetchone()
            teacher_name = str((teacher['real_name'] if teacher else '') or '').strip()
            q += ' AND r.status = ? AND p.advisor_name = ?'
            params = ['pending_teacher', teacher_name]
        elif role == ROLES['COLLEGE_APPROVER']:
            cu = conn.execute('SELECT college FROM users WHERE id = ?', (user_id,)).fetchone()
            c = str((cu['college'] if cu else '') or '').strip()
            q += ' AND r.status = ? AND p.college = ?'
            params = ['pending_college', c]
        else:
            if status:
                q += ' AND r.status = ?'
                params.append(status)
            else:
                q += " AND r.status = 'pending_school'"

        q += ' ORDER BY r.created_at DESC, r.id DESC LIMIT 200'
        rows = conn.execute(q, params).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d['legacy_title'] = sanitize_public_text(d.get('legacy_title'))
            d['reason'] = sanitize_public_text(d.get('reason'))
            out.append(d)
        return success(data=out)
    except Exception as e:
        return fail(str(e), 500)
    finally:
        conn.close()


@projects_bp.route('/legacy/borrow-requests/<int:req_id>/mentor-review', methods=['PUT'])
@login_required
@role_required([ROLES['TEACHER']])
def mentor_review_legacy_borrow(req_id):
    user_id = session.get('user_id')
    data = request.json or {}
    action = (data.get('action') or '').strip()
    opinion = sanitize_public_text(data.get('opinion') or data.get('review_comment'))
    if action not in ['approve', 'reject']:
        return fail('参数错误', 400)
    if not opinion:
        return fail('审核意见必填', 400)
    conn = get_db_connection()
    try:
        r = conn.execute('SELECT * FROM legacy_borrow_requests WHERE id = ?', (req_id,)).fetchone()
        if not r:
            return fail('记录不存在', 404)
        rd = dict(r)
        if (rd.get('status') or '') != 'pending_teacher':
            return fail('当前状态不可进行导师审核', 400)
        legacy = conn.execute('SELECT id, title, original_project_id FROM project_legacy WHERE id = ?', (rd['legacy_id'],)).fetchone()
        if not legacy:
            return fail('经验库项目不存在', 404)
        proj = conn.execute('SELECT id, title, advisor_name, college FROM projects WHERE id = ?', (legacy['original_project_id'],)).fetchone()
        if not proj:
            return fail('原项目不存在', 404)
        teacher = conn.execute('SELECT real_name, status FROM users WHERE id = ?', (user_id,)).fetchone()
        if not teacher or str(teacher['status'] or '').strip() != 'active':
            return fail('导师账号未通过审核或已禁用', 403)
        teacher_name = str((teacher['real_name'] if teacher else '') or '').strip()
        if not teacher_name or str(proj['advisor_name'] or '').strip() != teacher_name:
            return fail('仅该项目指导教师可审核', 403)

        applicant_id = int(rd.get('user_id') or 0)
        if action == 'approve':
            conn.execute(
                '''
                UPDATE legacy_borrow_requests
                SET status = 'pending_college', reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP, review_comment = ?
                WHERE id = ?
                ''',
                (user_id, opinion, req_id)
            )
            create_role_notifications(conn, ROLES['COLLEGE_APPROVER'], '待学院审核借鉴申请', f"受控项目《{sanitize_public_text(legacy['title'])}》有新的借鉴申请待学院审核。", college=proj['college'])
            create_notification(conn, applicant_id, '借鉴申请导师审核通过', f"受控项目《{sanitize_public_text(legacy['title'])}》借鉴申请已通过导师审核，进入学院审核。", 'approval')
            log_action(conn, user_id, 'LEGACY_BORROW_REVIEW_TEACHER', json.dumps({'request_id': req_id, 'legacy_id': int(legacy['id']), 'action': 'approve'}, ensure_ascii=False), request.remote_addr)
            conn.commit()
            return success(message='已通过，提交学院审核')
        conn.execute(
            '''
            UPDATE legacy_borrow_requests
            SET status = 'rejected', reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP, review_comment = ?
            WHERE id = ?
            ''',
            (user_id, opinion, req_id)
        )
        create_notification(conn, applicant_id, '借鉴申请被驳回', f"受控项目《{sanitize_public_text(legacy['title'])}》借鉴申请被导师驳回：{opinion}", 'approval')
        log_action(conn, user_id, 'LEGACY_BORROW_REVIEW_TEACHER', json.dumps({'request_id': req_id, 'legacy_id': int(legacy['id']), 'action': 'reject'}, ensure_ascii=False), request.remote_addr)
        conn.commit()
        return success(message='已驳回')
    except Exception as e:
        conn.rollback()
        return fail(str(e), 500)
    finally:
        conn.close()


@projects_bp.route('/legacy/borrow-requests/<int:req_id>/college-review', methods=['PUT'])
@login_required
@role_required([ROLES['COLLEGE_APPROVER']])
def college_review_legacy_borrow(req_id):
    user_id = session.get('user_id')
    data = request.json or {}
    action = (data.get('action') or '').strip()
    opinion = sanitize_public_text(data.get('opinion') or data.get('review_comment'))
    if action not in ['approve', 'reject']:
        return fail('参数错误', 400)
    if not opinion:
        return fail('审核意见必填', 400)
    conn = get_db_connection()
    try:
        r = conn.execute('SELECT * FROM legacy_borrow_requests WHERE id = ?', (req_id,)).fetchone()
        if not r:
            return fail('记录不存在', 404)
        rd = dict(r)
        if (rd.get('status') or '') != 'pending_college':
            return fail('当前状态不可进行学院审核', 400)
        legacy = conn.execute('SELECT id, title, original_project_id FROM project_legacy WHERE id = ?', (rd['legacy_id'],)).fetchone()
        if not legacy:
            return fail('经验库项目不存在', 404)
        proj = conn.execute('SELECT id, college FROM projects WHERE id = ?', (legacy['original_project_id'],)).fetchone()
        if not proj:
            return fail('原项目不存在', 404)
        cu = conn.execute('SELECT college FROM users WHERE id = ?', (user_id,)).fetchone()
        if str((cu['college'] if cu else '') or '').strip() != str(proj['college'] or '').strip():
            return fail('仅本学院审批人可审核', 403)

        applicant_id = int(rd.get('user_id') or 0)
        if action == 'approve':
            conn.execute(
                '''
                UPDATE legacy_borrow_requests
                SET status = 'pending_school', reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP, review_comment = ?
                WHERE id = ?
                ''',
                (user_id, opinion, req_id)
            )
            create_role_notifications(conn, ROLES['SCHOOL_APPROVER'], '待学校审核借鉴申请', f"受控项目《{sanitize_public_text(legacy['title'])}》有新的借鉴申请待学校审核。")
            create_notification(conn, applicant_id, '借鉴申请学院审核通过', f"受控项目《{sanitize_public_text(legacy['title'])}》借鉴申请已通过学院审核，进入学校审核。", 'approval')
            log_action(conn, user_id, 'LEGACY_BORROW_REVIEW_COLLEGE', json.dumps({'request_id': req_id, 'legacy_id': int(legacy['id']), 'action': 'approve'}, ensure_ascii=False), request.remote_addr)
            conn.commit()
            return success(message='已通过，提交学校审核')
        conn.execute(
            '''
            UPDATE legacy_borrow_requests
            SET status = 'rejected', reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP, review_comment = ?
            WHERE id = ?
            ''',
            (user_id, opinion, req_id)
        )
        create_notification(conn, applicant_id, '借鉴申请被驳回', f"受控项目《{sanitize_public_text(legacy['title'])}》借鉴申请被学院驳回：{opinion}", 'approval')
        log_action(conn, user_id, 'LEGACY_BORROW_REVIEW_COLLEGE', json.dumps({'request_id': req_id, 'legacy_id': int(legacy['id']), 'action': 'reject'}, ensure_ascii=False), request.remote_addr)
        conn.commit()
        return success(message='已驳回')
    except Exception as e:
        conn.rollback()
        return fail(str(e), 500)
    finally:
        conn.close()


@projects_bp.route('/legacy/borrow-requests/<int:req_id>/school-review', methods=['PUT'])
@login_required
@role_required([ROLES['SCHOOL_APPROVER']])
def school_review_legacy_borrow(req_id):
    user_id = session.get('user_id')
    data = request.json or {}
    action = (data.get('action') or '').strip()
    opinion = sanitize_public_text(data.get('opinion') or data.get('review_comment'))
    if action not in ['approve', 'reject']:
        return fail('参数错误', 400)
    if not opinion:
        return fail('审核意见必填', 400)
    conn = get_db_connection()
    try:
        r = conn.execute('SELECT * FROM legacy_borrow_requests WHERE id = ?', (req_id,)).fetchone()
        if not r:
            return fail('记录不存在', 404)
        rd = dict(r)
        if (rd.get('status') or '') != 'pending_school':
            return fail('当前状态不可进行学校审核', 400)
        legacy = conn.execute('SELECT id, title FROM project_legacy WHERE id = ?', (rd['legacy_id'],)).fetchone()
        if not legacy:
            return fail('经验库项目不存在', 404)
        applicant_id = int(rd.get('user_id') or 0)
        if action == 'approve':
            conn.execute(
                '''
                UPDATE legacy_borrow_requests
                SET status = 'approved', reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP, review_comment = ?
                WHERE id = ?
                ''',
                (user_id, opinion, req_id)
            )
            prev = conn.execute(
                "SELECT 1 FROM legacy_borrow_requests WHERE legacy_id = ? AND user_id = ? AND status = 'approved' AND id <> ? LIMIT 1",
                (rd['legacy_id'], applicant_id, req_id)
            ).fetchone()
            if not prev:
                applicant = conn.execute('SELECT role FROM users WHERE id = ?', (applicant_id,)).fetchone()
                applicant_role = (applicant['role'] if applicant else '')
                if applicant_role != ROLES['TEACHER']:
                    conn.execute('UPDATE project_legacy SET borrowed_count = borrowed_count + 1 WHERE id = ?', (rd['legacy_id'],))
            create_notification(conn, applicant_id, '借鉴申请审核通过', f"受控项目《{sanitize_public_text(legacy['title'])}》借鉴申请已通过审核，已解锁查看/下载权限。", 'approval')
            log_action(conn, user_id, 'LEGACY_BORROW_REVIEW_SCHOOL', json.dumps({'request_id': req_id, 'legacy_id': int(legacy['id']), 'action': 'approve'}, ensure_ascii=False), request.remote_addr)
            conn.commit()
            return success(message='已通过并解锁')
        conn.execute(
            '''
            UPDATE legacy_borrow_requests
            SET status = 'rejected', reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP, review_comment = ?
            WHERE id = ?
            ''',
            (user_id, opinion, req_id)
        )
        create_notification(conn, applicant_id, '借鉴申请被驳回', f"受控项目《{sanitize_public_text(legacy['title'])}》借鉴申请被学校驳回：{opinion}", 'approval')
        log_action(conn, user_id, 'LEGACY_BORROW_REVIEW_SCHOOL', json.dumps({'request_id': req_id, 'legacy_id': int(legacy['id']), 'action': 'reject'}, ensure_ascii=False), request.remote_addr)
        conn.commit()
        return success(message='已驳回')
    except Exception as e:
        conn.rollback()
        return fail(str(e), 500)
    finally:
        conn.close()


@projects_bp.route('/legacy/<int:legacy_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def legacy_detail(legacy_id):
    conn = get_db_connection()
    role = session.get('role')
    user_id = session.get('user_id')
    try:
        legacy = conn.execute('SELECT * FROM project_legacy WHERE id = ?', (legacy_id,)).fetchone()
        if not legacy:
            return fail('经验库项目不存在', 404)
        legacy_dict = dict(legacy)
        
        if request.method == 'GET':
            if not can_bypass_legacy_declaration(role):
                if not can_access_legacy_library(conn, user_id, role):
                    return fail('仅校内实名认证师生可访问经验库', 403)
                if (legacy_dict.get('status') or '') != 'approved':
                    return fail('无权限', 403)
                is_public = int(legacy_dict.get('is_public') or 0) == 1
                if role != ROLES['TEACHER']:
                    if is_public:
                        borrowed = conn.execute(
                            'SELECT 1 FROM project_borrow_records WHERE legacy_id = ? AND user_id = ?',
                            (legacy_id, user_id)
                        ).fetchone()
                        if not borrowed:
                            return fail('请先借鉴并同意版权合规声明后查看', 403)
                    else:
                        unlock = get_user_legacy_unlock_status(conn, legacy_id, user_id)
                        if not unlock.get('unlocked'):
                            return fail('该项目为涉密/受控级，请先申请借鉴并通过审核', 403)
                log_action(conn, user_id, 'LEGACY_VIEW', json.dumps({'legacy_id': legacy_id}, ensure_ascii=False), request.remote_addr)
            
            legacy_dict['title'] = sanitize_public_text(legacy_dict.get('title'))
            legacy_dict['project_summary'] = sanitize_public_text(legacy_dict.get('project_summary'))
            legacy_dict['methodology_summary'] = sanitize_public_text(legacy_dict.get('methodology_summary'))
            legacy_dict['expert_comments'] = sanitize_public_text(legacy_dict.get('expert_comments'))
            legacy_dict['industry_field'] = sanitize_public_text(legacy_dict.get('industry_field'))
            legacy_dict['team_experience'] = sanitize_public_text(legacy_dict.get('team_experience'))
            legacy_dict['pitfalls'] = sanitize_public_text(legacy_dict.get('pitfalls'))
            legacy_dict['business_model_overview'] = sanitize_public_text(legacy_dict.get('business_model_overview'))
            legacy_dict['award_level_label'] = award_level_label(legacy_dict.get('award_level'))
            
            base_info = {}
            orig_id = legacy_dict.get('original_project_id')
            if orig_id:
                proj = conn.execute('SELECT id, title, status, advisor_name, created_at, provincial_award_level, national_award_level FROM projects WHERE id = ?', (orig_id,)).fetchone()
                if proj:
                    if (not can_bypass_legacy_declaration(role)) and str(proj['status'] or '').strip() not in ['rated', 'finished', 'finished_national_award']:
                        return fail('该项目未结题，暂未入库', 403)
                    base_info['project_id'] = proj['id']
                    base_info['project_title'] = sanitize_public_text(proj['title'])
                    base_info['advisor_name'] = mask_name(proj['advisor_name'])
                    base_info['created_at'] = proj['created_at']
                    nat_lv = str(proj['national_award_level'] or '').strip()
                    prov_lv = str(proj['provincial_award_level'] or '').strip()
                    stage = 'national' if nat_lv and nat_lv != 'none' else ('provincial' if prov_lv and prov_lv != 'none' else '')
                    stage_label = '国赛' if stage == 'national' else ('省赛' if stage == 'provincial' else '')
                    legacy_dict['award_stage'] = stage
                    legacy_dict['award_stage_label'] = stage_label
                    award_text = str(legacy_dict.get('award_level_label') or '').strip()
                    if stage_label and award_text:
                        legacy_dict['award_level_display'] = f'{stage_label}·{award_text}'
                    else:
                        legacy_dict['award_level_display'] = award_text
                    members = conn.execute('SELECT name, is_leader FROM project_members WHERE project_id = ?', (orig_id,)).fetchall()
                    masked_members = []
                    for m in members:
                        masked_members.append({'name': mask_name(m['name']), 'role': '队长' if int(m['is_leader'] or 0) == 1 else '成员'})
                    base_info['team'] = masked_members
            
            awards = []
            if orig_id:
                rows = conn.execute(
                    'SELECT stage, award_level, award_name, award_time, issuer, created_at FROM project_awards WHERE project_id = ? ORDER BY created_at DESC',
                    (orig_id,)
                ).fetchall()
                for r in rows:
                    awards.append({
                        'stage': r['stage'],
                        'award_level': r['award_level'],
                        'award_level_label': award_level_label(r['award_level']),
                        'award_name': sanitize_public_text(r['award_name']),
                        'award_time': sanitize_public_text(r['award_time']),
                        'issuer': sanitize_public_text(r['issuer']),
                        'created_at': r['created_at']
                    })
            
            files = []
            if can_bypass_legacy_declaration(role):
                file_rows = conn.execute(
                    'SELECT id, file_type, original_filename, created_at, status, reject_reason FROM legacy_files WHERE legacy_id = ? ORDER BY created_at DESC',
                    (legacy_id,)
                ).fetchall()
            else:
                file_rows = conn.execute(
                    "SELECT id, file_type, original_filename, created_at, status, reject_reason FROM legacy_files WHERE legacy_id = ? AND status != 'rejected' ORDER BY created_at DESC",
                    (legacy_id,)
                ).fetchall()
            for fr in file_rows:
                frd = dict(fr)
                files.append({
                    'id': frd.get('id'),
                    'file_type': frd.get('file_type'),
                    'name': frd.get('original_filename') or '',
                    'created_at': frd.get('created_at'),
                    'status': frd.get('status'),
                    'reject_reason': frd.get('reject_reason'),
                    'download_url': f'/api/legacy/files/{frd.get("id")}/download'
                })
            
            legacy_dict['base_info'] = base_info
            legacy_dict['awards'] = awards
            legacy_dict['files'] = files
            return success(data=legacy_dict)
        
        if not can_manage_legacy(role):
            return fail('无权限', 403)
        
        if request.method == 'DELETE':
            conn.execute('DELETE FROM project_legacy WHERE id = ?', (legacy_id,))
            conn.commit()
            return success(message='已删除')
        
        data = request.json or {}
        updates = {}
        allowed = ['title', 'methodology_summary', 'expert_comments', 'industry_field', 'team_experience', 'pitfalls', 'business_model_overview', 'ppt_url']
        for k in allowed:
            if k in data:
                updates[k] = sanitize_public_text(data.get(k))
        if 'is_public' in data:
            updates['is_public'] = 1 if str(data.get('is_public')) in ['1', 'true', 'True'] else 0
        if 'award_level' in data:
            updates['award_level'] = normalize_award_level(data.get('award_level'))
        if 'project_type' in data:
            updates['project_type'] = (data.get('project_type') or '').strip()
        if not updates:
            return success(message='无变更')
        cols = ', '.join([f"{k} = ?" for k in updates.keys()])
        params = list(updates.values()) + [legacy_id]
        conn.execute(f'UPDATE project_legacy SET {cols} WHERE id = ?', params)
        conn.commit()
        return success(message='已更新')
    except Exception as e:
        conn.rollback()
        return fail(str(e), 500)
    finally:
        conn.close()


@projects_bp.route('/legacy/<int:legacy_id>/review', methods=['PUT'])
@login_required
def review_legacy(legacy_id):
    role = session.get('role')
    if not can_manage_legacy(role):
        return fail('无权限', 403)
    data = request.json or {}
    action = (data.get('action') or '').strip()
    is_public = 1 if str(data.get('is_public', 1)) in ['1', 'true', 'True'] else 0
    review_opinion = sanitize_public_text(data.get('review_opinion') or data.get('reject_reason'))
    user_id = session.get('user_id')
    
    if action not in ['approve', 'reject']:
        return fail('参数错误', 400)
    if not review_opinion:
        return fail('审核意见必填', 400)
        
    conn = get_db_connection()
    try:
        legacy = conn.execute('SELECT * FROM project_legacy WHERE id = ?', (legacy_id,)).fetchone()
        if not legacy:
            return fail('经验库项目不存在', 404)
        legacy_dict = dict(legacy)
        if (legacy_dict.get('status') or '').strip() not in ['pending_school', 'pending']:
            return fail('当前状态不可进行学校审核', 400)
        project = conn.execute(
            '''
            SELECT p.*, c.template_type AS competition_template_type, c.title AS competition_title
            FROM projects p
            LEFT JOIN competitions c ON p.competition_id = c.id
            WHERE p.id = ?
            ''',
            (legacy_dict.get('original_project_id'),)
        ).fetchone()
        if not project:
            return fail('原项目不存在', 404)
        p = dict(project)
        try:
            info = json.loads(p.get('extra_info') or '{}')
        except Exception:
            info = {}
        if action == 'approve':
            resolved_template = resolve_template_name(p)
            if not is_legacy_collection_ready(p, info, resolved_template):
                return fail('该项目未结题或不符合入库条件，无法通过', 400)
            conn.execute(
                '''
                UPDATE project_legacy
                SET status = 'approved', is_public = ?, reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP, reject_reason = NULL
                WHERE id = ?
                ''',
                (is_public, user_id, legacy_id)
            )
            info['experience_status'] = 'approved'
            info['experience_school_opinion'] = review_opinion
            info = append_experience_audit_log(info, role='school_approver', action='approve', opinion=review_opinion, reviewer_id=user_id)
            conn.execute('UPDATE projects SET extra_info = ? WHERE id = ?', (json.dumps(info, ensure_ascii=False), p['id']))
            create_notification(conn, p['created_by'], '经验内容已收录', f"项目《{p['title']}》经验内容学校审核已通过并入库。", 'approval')
            advisor_name = str(p.get('advisor_name') or '').strip()
            if advisor_name:
                for tid in resolve_teacher_user_ids(conn, advisor_name):
                    create_notification(conn, tid, '经验内容已收录', f"项目《{p['title']}》经验内容学校审核已通过并入库。", 'approval')
            conn.commit()
            return success(message='已通过并入库')
        conn.execute(
            '''
            UPDATE project_legacy
            SET status = 'pending_teacher', is_public = 0, reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP, reject_reason = ?
            WHERE id = ?
            ''',
            (user_id, review_opinion, legacy_id)
        )
        info['experience_status'] = 'pending_teacher'
        info['experience_school_opinion'] = review_opinion
        info = append_experience_audit_log(info, role='school_approver', action='reject', opinion=review_opinion, reviewer_id=user_id)
        conn.execute('UPDATE projects SET extra_info = ? WHERE id = ?', (json.dumps(info, ensure_ascii=False), p['id']))
        create_notification(conn, p['created_by'], '经验内容学校审核驳回', f"项目《{p['title']}》经验内容被学校驳回，已退回导师审核。", 'approval')
        advisor_name = str(p.get('advisor_name') or '').strip()
        if advisor_name:
            for tid in resolve_teacher_user_ids(conn, advisor_name):
                create_notification(conn, tid, '待导师复审经验内容', f"项目《{p['title']}》经验内容被学校驳回，请导师复审。", 'approval')
        conn.commit()
        return success(message='已驳回并退回导师审核')
    except Exception as e:
        conn.rollback()
        return fail(str(e), 500)
    finally:
        conn.close()

@projects_bp.route('/legacy/<int:legacy_id>/mentor-review', methods=['PUT'])
@login_required
@role_required([ROLES['TEACHER']])
def mentor_review_legacy(legacy_id):
    user_id = session.get('user_id')
    data = request.json or {}
    action = (data.get('action') or '').strip()
    opinion = sanitize_public_text(data.get('opinion'))
    if action not in ['approve', 'reject']:
        return fail('参数错误', 400)
    if not opinion:
        return fail('审核意见必填', 400)
    conn = get_db_connection()
    try:
        legacy = conn.execute('SELECT * FROM project_legacy WHERE id = ?', (legacy_id,)).fetchone()
        if not legacy:
            return fail('经验库项目不存在', 404)
        legacy_dict = dict(legacy)
        if (legacy_dict.get('status') or '').strip() != 'pending_teacher':
            return fail('当前状态不可进行导师审核', 400)
        project = conn.execute(
            '''
            SELECT p.*, c.template_type AS competition_template_type, c.title AS competition_title
            FROM projects p
            LEFT JOIN competitions c ON p.competition_id = c.id
            WHERE p.id = ?
            ''',
            (legacy_dict.get('original_project_id'),)
        ).fetchone()
        if not project:
            return fail('原项目不存在', 404)
        p = dict(project)
        teacher = conn.execute('SELECT real_name FROM users WHERE id = ?', (user_id,)).fetchone()
        teacher_name = str((teacher['real_name'] if teacher else '') or '').strip()
        if not teacher_name:
            return fail('导师信息异常', 400)
        if str(p.get('advisor_name') or '').strip() != teacher_name:
            return fail('仅项目指导教师可审核', 403)
        try:
            info = json.loads(p.get('extra_info') or '{}')
        except Exception:
            info = {}
        if action == 'approve':
            resolved_template = resolve_template_name(p)
            if not is_legacy_collection_ready(p, info, resolved_template):
                return fail('该项目未结题或不符合入库条件，无法提交学校审核', 400)
            conn.execute(
                "UPDATE project_legacy SET status = 'pending_school', reject_reason = NULL WHERE id = ?",
                (legacy_id,)
            )
            info['experience_status'] = 'pending_school'
            info['experience_teacher_opinion'] = opinion
            info = append_experience_audit_log(info, role='teacher', action='approve', opinion=opinion, reviewer_id=user_id)
            conn.execute('UPDATE projects SET extra_info = ? WHERE id = ?', (json.dumps(info, ensure_ascii=False), p['id']))
            create_role_notifications(
                conn,
                ROLES['SCHOOL_APPROVER'],
                '待学校审核经验内容',
                f"项目《{p['title']}》经验内容已通过导师审核，请完成学校脱敏终审。",
                exclude_user_id=user_id
            )
            create_notification(conn, p['created_by'], '经验内容导师审核通过', f"项目《{p['title']}》经验内容已通过导师审核，进入学校审核。", 'approval')
            conn.commit()
            return success(message='导师审核通过，已提交学校审核')
        conn.execute(
            "UPDATE project_legacy SET status = 'unsubmitted', reject_reason = ?, reviewed_by = NULL, reviewed_at = NULL WHERE id = ?",
            (opinion, legacy_id)
        )
        info['experience_status'] = 'unsubmitted'
        info['experience_teacher_opinion'] = opinion
        info = append_experience_audit_log(info, role='teacher', action='reject', opinion=opinion, reviewer_id=user_id)
        conn.execute('UPDATE projects SET extra_info = ? WHERE id = ?', (json.dumps(info, ensure_ascii=False), p['id']))
        create_notification(conn, p['created_by'], '经验内容导师审核驳回', f"项目《{p['title']}》经验内容被导师驳回，请修改后重新提交。", 'approval')
        conn.commit()
        return success(message='导师已驳回，学生可修改后重提')
    except Exception as e:
        conn.rollback()
        return fail(str(e), 500)
    finally:
        conn.close()


@projects_bp.route('/legacy/<int:legacy_id>/pitfalls-suggestion', methods=['POST'])
@login_required
@role_required([ROLES['TEACHER']])
def submit_pitfalls_suggestion(legacy_id):
    data = request.json or {}
    content = sanitize_public_text(data.get('content'))
    if not content:
        return fail('避坑指南不能为空', 400)
    if len(content) > 2000:
        return fail('避坑指南过长', 400)
    teacher_id = session.get('user_id')
    
    conn = get_db_connection()
    try:
        legacy = conn.execute('SELECT id, status, is_public FROM project_legacy WHERE id = ?', (legacy_id,)).fetchone()
        if not legacy:
            return fail('经验库项目不存在', 404)
        if (legacy['status'] or '') != 'approved' or int(legacy['is_public'] or 0) != 1:
            return fail('该经验库项目未公开', 403)
        conn.execute(
            'INSERT INTO legacy_pitfall_suggestions (legacy_id, teacher_id, content) VALUES (?, ?, ?)',
            (legacy_id, teacher_id, content)
        )
        conn.commit()
        return success(message='已提交，等待审核')
    except Exception as e:
        conn.rollback()
        return fail(str(e), 500)
    finally:
        conn.close()


@projects_bp.route('/legacy/pitfalls-suggestions/<int:suggestion_id>/review', methods=['PUT'])
@login_required
def review_pitfalls_suggestion(suggestion_id):
    role = session.get('role')
    if not can_manage_legacy(role):
        return fail('无权限', 403)
    data = request.json or {}
    action = (data.get('action') or '').strip()
    review_comment = sanitize_public_text(data.get('review_comment'))
    if action not in ['approve', 'reject']:
        return fail('参数错误', 400)
    if action == 'reject' and not review_comment:
        return fail('驳回原因必填', 400)
    user_id = session.get('user_id')
    
    conn = get_db_connection()
    try:
        s = conn.execute('SELECT * FROM legacy_pitfall_suggestions WHERE id = ?', (suggestion_id,)).fetchone()
        if not s:
            return fail('记录不存在', 404)
        if (s['status'] or '') != 'pending':
            return fail('记录已处理', 400)
        if action == 'approve':
            conn.execute(
                '''
                UPDATE legacy_pitfall_suggestions
                SET status = 'approved', reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP, review_comment = NULL
                WHERE id = ?
                ''',
                (user_id, suggestion_id)
            )
            conn.execute(
                '''
                UPDATE project_legacy
                SET pitfalls = CASE WHEN pitfalls IS NULL OR pitfalls = '' THEN ? ELSE pitfalls || '\n' || ? END
                WHERE id = ?
                ''',
                (s['content'], s['content'], s['legacy_id'])
            )
            conn.commit()
            return success(message='已通过并更新经验库')
        conn.execute(
            '''
            UPDATE legacy_pitfall_suggestions
            SET status = 'rejected', reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP, review_comment = ?
            WHERE id = ?
            ''',
            (user_id, review_comment, suggestion_id)
        )
        conn.commit()
        return success(message='已驳回')
    except Exception as e:
        conn.rollback()
        return fail(str(e), 500)
    finally:
        conn.close()


@projects_bp.route('/legacy/<int:legacy_id>/files', methods=['POST'])
@login_required
def upload_legacy_file(legacy_id):
    role = session.get('role')
    if not can_manage_legacy(role):
        return fail('无权限', 403)
    file_type = (request.form.get('file_type') or '').strip()
    if file_type not in ['route_map', 'photo', 'attachment', 'compliance_material']:
        return fail('文件类型无效', 400)
    if 'file' not in request.files:
        return fail('未选择文件', 400)
    f = request.files['file']
    if not f or not f.filename:
        return fail('未选择文件', 400)
        
    conn = get_db_connection()
    try:
        legacy = conn.execute('SELECT id FROM project_legacy WHERE id = ?', (legacy_id,)).fetchone()
        if not legacy:
            return fail('经验库项目不存在', 404)
            
        base = current_app.config.get('UPLOAD_FOLDER') or 'static/uploads'
        legacy_dir = os.path.join(base, 'legacy')
        os.makedirs(legacy_dir, exist_ok=True)
        
        filename = secure_filename(f.filename)
        ts = datetime.now().strftime('%Y%m%d%H%M%S%f')
        stored_name = f'{legacy_id}_{file_type}_{ts}_{filename}'
        stored_path = os.path.join(legacy_dir, stored_name)
        f.save(stored_path)
        
        conn.execute(
            '''
            INSERT INTO legacy_files (legacy_id, file_type, stored_path, original_filename, uploaded_by, status, reviewed_by, reviewed_at)
            VALUES (?, ?, ?, ?, ?, 'approved', ?, CURRENT_TIMESTAMP)
            ''',
            (legacy_id, file_type, stored_path, filename, session.get('user_id'), session.get('user_id'))
        )
        conn.commit()
        return success(message='已上传')
    except Exception as e:
        conn.rollback()
        return fail(str(e), 500)
    finally:
        conn.close()


@projects_bp.route('/legacy/files/<int:file_id>/download', methods=['GET'])
@login_required
def download_legacy_file(file_id):
    role = session.get('role')
    user_id = session.get('user_id')
    conn = get_db_connection()
    try:
        row = conn.execute(
            'SELECT f.*, l.is_public, l.status AS legacy_status FROM legacy_files f JOIN project_legacy l ON f.legacy_id = l.id WHERE f.id = ?',
            (file_id,)
        ).fetchone()
        if not row:
            return fail('文件不存在', 404)
        legacy_id = int(row['legacy_id'] or 0)
        if not can_bypass_legacy_declaration(role):
            if not can_access_legacy_library(conn, user_id, role):
                return fail('仅校内实名认证师生可下载', 403)
            if (row['legacy_status'] or '') != 'approved' or (row['status'] or '') == 'rejected':
                return fail('无权限下载', 403)
            is_public = int(row['is_public'] or 0) == 1
            if role != ROLES['TEACHER']:
                if is_public:
                    borrowed = conn.execute(
                        'SELECT 1 FROM project_borrow_records WHERE legacy_id = ? AND user_id = ?',
                        (legacy_id, user_id)
                    ).fetchone()
                    if not borrowed:
                        return fail('请先借鉴并同意版权合规声明后下载', 403)
                else:
                    unlock = get_user_legacy_unlock_status(conn, legacy_id, user_id)
                    if not unlock.get('unlocked'):
                        return fail('该项目为涉密/受控级，请先申请借鉴并通过审核', 403)
        path = row['stored_path']
        if not path or not os.path.exists(path):
            return fail('文件不存在', 404)
        log_action(conn, user_id, 'LEGACY_DOWNLOAD', json.dumps({'legacy_id': legacy_id, 'file_id': file_id}, ensure_ascii=False), request.remote_addr)
        conn.commit()

        download_name = row['original_filename'] or os.path.basename(path)
        ext = os.path.splitext(download_name)[1].lower()
        wm_text = f"{getattr(config, 'WATERMARK_SCHOOL_NAME', 'XX大学')}双创经验库 仅供校内学习使用 禁止商用"

        def escape_pdf_text(s):
            return (s or '').replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')

        if ext in ['.png', '.jpg', '.jpeg', '.webp'] or ext == '.pdf':
            try:
                from io import BytesIO
                if ext in ['.png', '.jpg', '.jpeg', '.webp']:
                    from PIL import Image, ImageDraw, ImageFont
                    img = Image.open(path).convert('RGBA')
                    overlay = Image.new('RGBA', img.size, (255, 255, 255, 0))
                    draw = ImageDraw.Draw(overlay)
                    font = ImageFont.load_default()
                    step_x = max(220, int(img.size[0] * 0.25))
                    step_y = max(160, int(img.size[1] * 0.20))
                    txt = wm_text
                    for y in range(-step_y, img.size[1] + step_y, step_y):
                        for x in range(-step_x, img.size[0] + step_x, step_x):
                            draw.text((x, y), txt, fill=(120, 120, 120, 60), font=font)
                    out = Image.alpha_composite(img, overlay)
                    buf = BytesIO()
                    if ext in ['.jpg', '.jpeg']:
                        out.convert('RGB').save(buf, format='JPEG', quality=92)
                    elif ext == '.webp':
                        out.convert('RGB').save(buf, format='WEBP', quality=92)
                    else:
                        out.save(buf, format='PNG')
                    buf.seek(0)
                    return send_file(buf, as_attachment=True, download_name=download_name)

                from pypdf import PdfReader, PdfWriter
                from pypdf import PageObject
                from pypdf.generic import NameObject, DictionaryObject, DecodedStreamObject

                reader = PdfReader(path)
                writer = PdfWriter()
                txt = escape_pdf_text(wm_text)

                def build_watermark_page(w, h):
                    page = PageObject.create_blank_page(width=w, height=h)
                    font = DictionaryObject({
                        NameObject('/Type'): NameObject('/Font'),
                        NameObject('/Subtype'): NameObject('/Type1'),
                        NameObject('/BaseFont'): NameObject('/Helvetica')
                    })
                    resources = DictionaryObject({
                        NameObject('/Font'): DictionaryObject({NameObject('/F1'): font})
                    })
                    page[NameObject('/Resources')] = resources

                    cos = 0.7071
                    sin = 0.7071
                    step_x = max(220, int(w * 0.32))
                    step_y = max(180, int(h * 0.28))
                    ops = ["q 0.85 g BT /F1 28 Tf"]
                    for y in range(-step_y, int(h + step_y), step_y):
                        for x in range(-step_x, int(w + step_x), step_x):
                            ops.append(f"{cos} {sin} {-sin} {cos} {x} {y} Tm ({txt}) Tj")
                    ops.append("ET Q")
                    stream = DecodedStreamObject()
                    stream.set_data(("\n".join(ops)).encode('utf-8'))
                    page[NameObject('/Contents')] = stream
                    return page

                for p in reader.pages:
                    w = float(p.mediabox.width)
                    h = float(p.mediabox.height)
                    wm_page = build_watermark_page(w, h)
                    p.merge_page(wm_page)
                    writer.add_page(p)

                buf = BytesIO()
                writer.write(buf)
                buf.seek(0)
                return send_file(buf, as_attachment=True, download_name=download_name)
            except Exception:
                pass

        return send_file(path, as_attachment=True, download_name=download_name)
    except Exception as e:
        return fail(str(e), 500)
    finally:
        conn.close()


@projects_bp.route('/legacy/files/<int:file_id>/review', methods=['PUT'])
@login_required
def review_legacy_file(file_id):
    role = session.get('role')
    if not can_manage_legacy(role):
        return fail('无权限', 403)
    data = request.json or {}
    action = (data.get('action') or '').strip()
    reject_reason = sanitize_public_text(data.get('reject_reason'))
    if action not in ['approve', 'reject']:
        return fail('参数错误', 400)
    if action == 'reject' and not reject_reason:
        return fail('驳回原因必填', 400)
        
    user_id = session.get('user_id')
    conn = get_db_connection()
    try:
        row = conn.execute('SELECT * FROM legacy_files WHERE id = ?', (file_id,)).fetchone()
        if not row:
            return fail('文件不存在', 404)
        if action == 'approve':
            conn.execute(
                '''
                UPDATE legacy_files
                SET status = 'approved', reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP, reject_reason = NULL
                WHERE id = ?
                ''',
                (user_id, file_id)
            )
            conn.commit()
            return success(message='已通过')
        conn.execute(
            '''
            UPDATE legacy_files
            SET status = 'rejected', reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP, reject_reason = ?
            WHERE id = ?
            ''',
            (user_id, reject_reason, file_id)
        )
        conn.commit()
        return success(message='已驳回')
    except Exception as e:
        conn.rollback()
        return fail(str(e), 500)
    finally:
        conn.close()
