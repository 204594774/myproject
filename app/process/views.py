from flask import Blueprint, request
from app.utils.db import get_db_connection
from app.utils.response import success, fail
from app.utils.auth import login_required, role_required
from config import get_config
import json

config = get_config()
ROLES = config.ROLES

process_template_bp = Blueprint('process_template', __name__, url_prefix='/api/process-template')


@process_template_bp.route('/<string:template_name>', methods=['GET'])
@login_required
def get_template_config(template_name):
    conn = get_db_connection()
    row = conn.execute(
        'SELECT id, template_name, process_structure, has_mid_check, has_final_acceptance FROM process_templates WHERE template_name = ?',
        (template_name,)
    ).fetchone()
    if not row:
        return fail('模板不存在', 404)

    template_id = row['id']
    nodes = conn.execute(
        'SELECT node_name, status_options FROM process_node_status WHERE template_id = ?',
        (template_id,)
    ).fetchall()
    node_status = {}
    for n in nodes:
        try:
            node_status[n['node_name']] = json.loads(n['status_options'] or '[]')
        except Exception:
            node_status[n['node_name']] = []

    award = conn.execute(
        'SELECT level_options FROM award_levels WHERE template_id = ?',
        (template_id,)
    ).fetchone()
    award_levels = []
    if award:
        try:
            award_levels = json.loads(award['level_options'] or '[]')
        except Exception:
            award_levels = []

    try:
        process_structure = json.loads(row['process_structure'] or '[]')
    except Exception:
        process_structure = []

    return success(data={
        'template_name': row['template_name'],
        'process_structure': process_structure,
        'has_mid_check': bool(row['has_mid_check']),
        'has_final_acceptance': bool(row['has_final_acceptance']),
        'node_status': node_status,
        'award_levels': award_levels
    })


@process_template_bp.route('/node-status', methods=['POST'])
@login_required
@role_required([ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN']])
def edit_node_status():
    data = request.json or {}
    template_name = (data.get('template_name') or '').strip()
    node_name = (data.get('node_name') or '').strip()
    status_options = data.get('status_options', [])
    if not template_name or not node_name:
        return fail('参数错误', 400)
    if not isinstance(status_options, list):
        return fail('status_options 必须为数组', 400)

    conn = get_db_connection()
    tpl = conn.execute(
        'SELECT id FROM process_templates WHERE template_name = ?',
        (template_name,)
    ).fetchone()
    if not tpl:
        return fail('模板不存在', 404)

    conn.execute(
        'INSERT OR REPLACE INTO process_node_status (template_id, node_name, status_options) VALUES (?, ?, ?)',
        (tpl['id'], node_name, json.dumps(status_options, ensure_ascii=False))
    )
    conn.commit()
    return success(message='节点状态配置成功')


@process_template_bp.route('/award-levels', methods=['POST'])
@login_required
@role_required([ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN']])
def edit_award_levels():
    data = request.json or {}
    template_name = (data.get('template_name') or '').strip()
    level_options = data.get('level_options', [])
    if not template_name:
        return fail('参数错误', 400)
    if not isinstance(level_options, list):
        return fail('level_options 必须为数组', 400)

    conn = get_db_connection()
    tpl = conn.execute(
        'SELECT id FROM process_templates WHERE template_name = ?',
        (template_name,)
    ).fetchone()
    if not tpl:
        return fail('模板不存在', 404)

    conn.execute(
        'INSERT OR REPLACE INTO award_levels (template_id, level_options) VALUES (?, ?)',
        (tpl['id'], json.dumps(level_options, ensure_ascii=False))
    )
    conn.commit()
    return success(message='获奖等级配置成功')

