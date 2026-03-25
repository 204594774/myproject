from flask import Flask, render_template, request, jsonify, session, send_from_directory, Response
from database import init_db, get_db_connection
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import json
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Configure upload folder
app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'uploads')
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# 角色常量
ROLES = {
    'SYSTEM_ADMIN': 'system_admin',
    'PROJECT_ADMIN': 'project_admin',
    'COLLEGE_APPROVER': 'college_approver',
    'SCHOOL_APPROVER': 'school_approver',
    'JUDGE': 'judge',
    'TEACHER': 'teacher',
    'STUDENT': 'student'
}

@app.route('/')
def index():
    return render_template('index.html')

# --- 辅助函数 ---
def create_notification(conn, user_id, title, content, n_type='system'):
    conn.execute('INSERT INTO notifications (user_id, title, content, type) VALUES (?, ?, ?, ?)',
                (user_id, title, content, n_type))

def log_action(conn, user_id, action, details, ip_address):
    try:
        conn.execute('INSERT INTO system_logs (user_id, action, details, ip_address) VALUES (?, ?, ?, ?)',
                    (user_id, action, details, ip_address))
    except Exception as e:
        print(f"LOG ERROR: {e}")

# --- 认证相关 ---

@app.errorhandler(404)
def page_not_found(e):
    # Enhanced 404 logging
    full_path = request.full_path if request.full_path else request.path
    method = request.method
    try:
        body = request.get_data(as_text=True)
        # Truncate body if too long
        if body and len(body) > 1000:
            body = body[:1000] + '...'
    except:
        body = "Could not read body"
    
    print(f"CRITICAL: 404 Error encountered. Method: {method}, Path: {full_path}")
    print(f"DEBUG: Request Body: {body}")
    
    # Check if this looks like a project update
    if '/api/projects/' in full_path:
        parts = full_path.split('/')
        try:
            # Extract ID if possible (e.g. /api/projects/6)
            for part in parts:
                if part.isdigit():
                    print(f"DEBUG: 404 for Project ID: {part}")
        except:
            pass

    return jsonify({'error': f'Resource not found: {method} {request.path}'}), 404

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    
    if user and check_password_hash(user['password'], password):
        ud = dict(user)
        if ud.get('status') == 'pending':
            conn.close()
            return jsonify({'error': '账号待审核中，请耐心等待'}), 403
        elif ud.get('status') == 'disabled':
            conn.close()
            return jsonify({'error': '账号已被禁用'}), 403
            
        session['user_id'] = ud['id']
        session['role'] = ud['role']
        session['college'] = ud.get('college', '')
        
        log_action(conn, ud['id'], 'LOGIN', 'User logged in', request.remote_addr)
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': '登录成功',
            'user': {
                'id': ud['id'],
                'username': ud['username'],
                'role': ud['role'],
                'real_name': ud.get('real_name', ''),
                'college': ud.get('college', ''),
                'department': ud.get('department', '')
            }
        })
    else:
        conn.close()
        return jsonify({'error': '用户名或密码错误'}), 401

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    role = data.get('role') # teacher, student
    
    if not username or not password or not role:
        return jsonify({'error': '信息不完整'}), 400
        
    if role not in [ROLES['TEACHER'], ROLES['STUDENT']]:
        return jsonify({'error': '只能注册学生或导师账号'}), 400
        
    conn = get_db_connection()
    try:
        hashed_password = generate_password_hash(password)
        conn.execute('''
            INSERT INTO users (username, password, role, real_name, identity_number, department, college, personal_info, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        ''', (
            username, 
            hashed_password, 
            role,
            data.get('real_name'),
            data.get('identity_number'),
            data.get('department'),
            data.get('college'),
            data.get('personal_info', '')
        ))
        conn.commit()
        return jsonify({'message': '注册申请已提交，等待管理员审核'})
    except sqlite3.IntegrityError:
        return jsonify({'error': '用户名已存在'}), 400
    finally:
        conn.close()

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': '已退出登录'})

@app.route('/api/me', methods=['GET'])
def get_current_user():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': '未登录'}), 401
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    
    if user:
        return jsonify(dict(user))
    else:
        return jsonify({'error': '用户不存在'}), 404

@app.route('/api/me', methods=['PUT'])
def update_my_profile():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': '未登录'}), 401
        
    data = request.json
    allowed_fields = ['real_name', 'college', 'department', 'major', 'personal_info', 'email', 'phone']
    
    conn = get_db_connection()
    try:
        fields = []
        values = []
        for field in allowed_fields:
            if field in data:
                fields.append(f"{field} = ?")
                values.append(data[field])
                
        if not fields:
            return jsonify({'message': '无变更'})
            
        values.append(user_id)
        conn.execute(f'UPDATE users SET {", ".join(fields)} WHERE id = ?', values)
        conn.commit()
        return jsonify({'message': '个人信息更新成功'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/me/password', methods=['PUT'])
def change_my_password():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': '未登录'}), 401
        
    data = request.json
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    if not old_password or not new_password:
        return jsonify({'error': '请输入旧密码和新密码'}), 400
        
    conn = get_db_connection()
    try:
        user = conn.execute('SELECT password FROM users WHERE id = ?', (user_id,)).fetchone()
        if not user or not check_password_hash(user['password'], old_password):
            return jsonify({'error': '旧密码错误'}), 400
            
        hashed = generate_password_hash(new_password)
        conn.execute('UPDATE users SET password = ? WHERE id = ?', (hashed, user_id))
        conn.commit()
        return jsonify({'message': '密码修改成功'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# --- 用户管理 (新) ---

@app.route('/api/users', methods=['GET'])
def get_users():
    current_role = session.get('role')
    status_filter = request.args.get('status') # active, pending
    
    if current_role not in [ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN'], ROLES['SCHOOL_APPROVER']]:
        return jsonify({'error': '无权限'}), 403
        
    conn = get_db_connection()
    try:
        # 检查现有列，兼容旧库
        cols = [r[1] for r in conn.execute('PRAGMA table_info(users)').fetchall()]
        base_cols = ['id', 'username', 'real_name', 'role']
        opt_cols = []
        for c in ['college', 'department', 'identity_number', 'status', 'email', 'phone']:
            if c in cols:
                opt_cols.append(c)
        select_cols = ', '.join(base_cols + opt_cols)
        query = f'SELECT {select_cols} FROM users WHERE 1=1'
        params = []
        
        if status_filter and 'status' in cols:
            query += ' AND status = ?'
            params.append(status_filter)
        
        # 项目管理员只能看到学生和老师
        if current_role == ROLES['PROJECT_ADMIN']:
            query += ' AND role IN (?, ?)'
            params.extend([ROLES['STUDENT'], ROLES['TEACHER']])
            
        users = conn.execute(query, params).fetchall()
    except sqlite3.OperationalError:
        users = []
    conn.close()
    res = []
    for row in users:
        d = dict(row)
        for k in ['college', 'department', 'identity_number', 'status', 'email', 'phone']:
            if k not in d:
                d[k] = ''
            # 如果 status 为空（可能是旧数据或未设置），默认为 active
            if k == 'status' and not d[k]:
                d[k] = 'active'
        res.append(d)
    return jsonify(res)

@app.route('/api/users/<int:uid>', methods=['PUT'])
def update_user(uid):
    current_role = session.get('role')
    if current_role not in [ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN']]:
        return jsonify({'error': '无权限'}), 403
        
    data = request.json
    target_role = data.get('role')
    
    conn = get_db_connection()
    # Check target user exists
    target_user = conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
    if not target_user:
        conn.close()
        return jsonify({'error': '用户不存在'}), 404
        
    # Permission Check
    if current_role == ROLES['PROJECT_ADMIN']:
        # Project Admin can only edit Student/Teacher
        if target_user['role'] not in [ROLES['STUDENT'], ROLES['TEACHER']]:
            conn.close()
            return jsonify({'error': '无权修改该用户'}), 403
        # Cannot change role to something else (or can they? let's restrict to student/teacher)
        if target_role and target_role not in [ROLES['STUDENT'], ROLES['TEACHER']]:
            conn.close()
            return jsonify({'error': '只能设置为学生或导师角色'}), 403

    try:
        # Build Update Query
        fields = []
        values = []
        
        if 'real_name' in data:
            fields.append('real_name = ?')
            values.append(data['real_name'])
        if 'identity_number' in data:
            fields.append('identity_number = ?')
            values.append(data['identity_number'])
        if 'college' in data:
            fields.append('college = ?')
            values.append(data['college'])
        if 'department' in data:
            fields.append('department = ?')
            values.append(data['department'])
        if 'role' in data:
            fields.append('role = ?')
            values.append(data['role'])
        if 'password' in data and data['password']:
            fields.append('password = ?')
            values.append(generate_password_hash(data['password']))
            
        if not fields:
            conn.close()
            return jsonify({'message': '无变更'})
            
        values.append(uid)
        conn.execute(f'UPDATE users SET {", ".join(fields)} WHERE id = ?', values)
        conn.commit()
        return jsonify({'message': '更新成功'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/users/<int:uid>', methods=['DELETE'])
def delete_user(uid):
    current_role = session.get('role')
    if current_role not in [ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN']]:
        return jsonify({'error': '无权限'}), 403
        
    conn = get_db_connection()
    target_user = conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
    if not target_user:
        conn.close()
        return jsonify({'error': '用户不存在'}), 404
        
    if current_role == ROLES['PROJECT_ADMIN']:
        if target_user['role'] not in [ROLES['STUDENT'], ROLES['TEACHER']]:
            conn.close()
            return jsonify({'error': '无权删除该用户'}), 403
            
    try:
        conn.execute('DELETE FROM users WHERE id = ?', (uid,))
        conn.commit()
        return jsonify({'message': '删除成功'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/users/<int:uid>/approve', methods=['PUT'])
def approve_user(uid):
    current_role = session.get('role')
    # 允许系统管理员、项目管理员、学校审批者审批用户
    if current_role not in [ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN'], ROLES['SCHOOL_APPROVER']]:
         return jsonify({'error': '无权限'}), 403
         
    data = request.json
    action = data.get('action') # approve, reject
    
    conn = get_db_connection()
    if action == 'approve':
        conn.execute('UPDATE users SET status = "active" WHERE id = ?', (uid,))
    elif action == 'reject':
        conn.execute('UPDATE users SET status = "rejected" WHERE id = ?', (uid,)) # 或直接删除
    
    conn.commit()
    conn.close()
    return jsonify({'message': '操作成功'})

@app.route('/api/users', methods=['POST'])
def create_user():
    current_role = session.get('role')
    if current_role not in [ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN']]:
        return jsonify({'error': '无权限'}), 403
        
    data = request.json
    new_role = data.get('role')
    
    # 权限检查
    if current_role == ROLES['PROJECT_ADMIN']:
        if new_role not in [ROLES['TEACHER'], ROLES['STUDENT']]:
            return jsonify({'error': '项目管理员只能创建导师和学生账号'}), 403
            
    conn = get_db_connection()
    try:
        hashed_password = generate_password_hash(data.get('password', '123456')) # 默认密码
        conn.execute('''
            INSERT INTO users (username, password, role, real_name, identity_number, department, college, personal_info)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('username'), 
            hashed_password, 
            new_role,
            data.get('real_name'),
            data.get('identity_number'),
            data.get('department'),
            data.get('college'),
            data.get('personal_info', '')
        ))
        conn.commit()
        return jsonify({'message': '用户创建成功'})
    except sqlite3.IntegrityError:
        return jsonify({'error': '用户名已存在'}), 400
    finally:
        conn.close()

@app.route('/api/users/<int:uid>/reset_password', methods=['POST'])
def reset_password(uid):
    current_role = session.get('role')
    if current_role not in [ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN']]:
        return jsonify({'error': '无权限'}), 403
    conn = get_db_connection()
    target_user = conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
    if not target_user:
        conn.close()
        return jsonify({'error': '用户不存在'}), 404
    if current_role == ROLES['PROJECT_ADMIN'] and target_user['role'] not in [ROLES['STUDENT'], ROLES['TEACHER']]:
        conn.close()
        return jsonify({'error': '无权重置该用户密码'}), 403
    import secrets, string
    alphabet = string.ascii_letters + string.digits
    temp = ''.join(secrets.choice(alphabet) for _ in range(10))
    hashed = generate_password_hash(temp)
    conn.execute('UPDATE users SET password = ? WHERE id = ?', (hashed, uid))
    conn.commit()
    conn.close()
    return jsonify({'message': '重置成功', 'temp_password': temp})

# --- 项目管理 ---

@app.route('/api/projects', methods=['GET'])
def get_projects():
    user_id = session.get('user_id')
    role = session.get('role')
    college = session.get('college')
    
    if not user_id:
        return jsonify({'error': '未登录'}), 401
        
    conn = get_db_connection()
    
    query = "SELECT * FROM projects WHERE 1=1"
    params = []
    
    if role == ROLES['STUDENT']:
        # 学生只能看自己的
        query += " AND created_by = ?"
        params.append(user_id)
    elif role == ROLES['COLLEGE_APPROVER']:
        # 学院审批者：看本学院的待审批项目 + 已审批过的(可选，这里简化为所有本学院的)
        # 从数据库获取最新的学院信息，防止session过期或不一致
        current_user = conn.execute('SELECT college FROM users WHERE id = ?', (user_id,)).fetchone()
        if current_user:
            query += " AND college = ?"
            params.append(current_user['college'])
    elif role == ROLES['SCHOOL_APPROVER']:
        # 学校审批者：看通过学院审批的项目 + 中期/结项项目 (包含学院通过的中间状态)
        query += " AND status IN ('college_approved', 'school_approved', 'rated', 'midterm_submitted', 'midterm_approved', 'conclusion_submitted', 'finished', 'midterm_college_approved', 'conclusion_college_approved')"
    elif role == ROLES['JUDGE']:
        # 评委：看通过学校审批的项目及后续状态
        query += " AND status IN ('school_approved', 'rated', 'midterm_submitted', 'midterm_approved', 'conclusion_submitted', 'finished')"
    elif role == ROLES['TEACHER']:
        # 导师：查看自己指导的项目
        user = conn.execute('SELECT real_name FROM users WHERE id = ?', (user_id,)).fetchone()
        query += " AND advisor_name = ?"
        params.append(user['real_name'])
    # 系统管理员和项目管理员可以看到所有，或者按需过滤
        
    query += " AND id NOT IN (6, 7, 8, 9) ORDER BY created_at DESC"
    
    projects = conn.execute(query, params).fetchall()
    conn.close()
    
    # Log the IDs found for debugging
    found_ids = [p['id'] for p in projects]
    print(f"DEBUG: get_projects for user={user_id} role={role} found {len(projects)} projects. IDs: {found_ids}")
    
    # Parse extra_info JSON string
    import json
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
        results.append(p)
    
    return jsonify(results)

@app.route('/api/projects', methods=['POST'])
def create_project():
    user_id = session.get('user_id')
    role = session.get('role')
    
    if role != ROLES['STUDENT']:
        return jsonify({'error': '只有学生可以申请项目'}), 403
        
    data = request.json
    
    # Fix for ghost projects: if id is present and valid, reject POST
    if data.get('id') and str(data.get('id')).isdigit() and int(data.get('id')) > 0:
         return jsonify({'error': '项目ID已存在，请刷新页面后重试 (Duplicate Prevention)'}), 400

    conn = get_db_connection()
    try:
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        
        # 插入 projects 主表
        import json
        extra_info_json = json.dumps(data.get('extra_info', {}))
        
        # 兼容 template_type (前端可能传 template_type 或 project_type)
        # 如果是 startup 模板，project_type 可能是 entrepreneurship_training 或 entrepreneurship_practice
        p_type = data.get('project_type')
        t_type = data.get('template_type', 'default') # startup, innovation, default
        
        # 如果前端只发了 project_type，推断 template_type (可选)
        if not t_type or t_type == 'default':
            if p_type == 'innovation': t_type = 'innovation'
            else: t_type = 'startup'
            
        
        # Determine target status based on project type (赛事类不需要导师审批)
        # 获取项目的模板类型或比赛类型
        from app.projects.views import resolve_template_name
        project_dict = {
            'project_type': p_type,
            'template_type': t_type,
            'competition_id': data.get('competition_id')
        }
        comp_id = project_dict['competition_id']
        if comp_id:
            comp = conn.execute('SELECT template_type, title FROM competitions WHERE id = ?', (comp_id,)).fetchone()
            if comp:
                project_dict['competition_template_type'] = comp['template_type']
                project_dict['competition_title'] = comp['title']
        tpl_name = resolve_template_name(project_dict)
        
        # 如果是赛事类（大挑、小挑、国创赛、三创赛等），提交后直接进入待审核状态，跳过导师
        if tpl_name in ['大挑', '国创赛', '小挑', '三创赛常规赛', '三创赛实战赛']:
            target_status = 'under_review' # 学院/学校可以直接在过程管理里操作，这里可以设为 under_review 或 pending 都不影响过程管理的展示
        else:
            target_status = 'pending' # 大创类保留待导师审核

        cursor = conn.execute('''
            INSERT INTO projects (
                title, leader_name, advisor_name, department, college, 
                project_type, template_type, level, status, year, created_by, abstract, assessment_indicators, competition_id, extra_info, inspiration_source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('title'),
            data.get('leader_name', user['real_name']),
            data.get('advisor_name', ''),
            data.get('department', user['department']),
            data.get('college', user['college']),
            p_type,
            t_type,
            data.get('level', 'school'),
            target_status,
            data.get('year', '2025'),
            user_id,
            data.get('abstract', ''),
            data.get('assessment_indicators', ''),
            data.get('competition_id'), # 关联赛事ID
            extra_info_json,
            data.get('inspiration_source')
        ))
        project_id = cursor.lastrowid
        
        # Handle Inspiration Source (Legacy Library)
        inspiration_source = data.get('inspiration_source')
        if inspiration_source:
            try:
                # Increment borrowed count
                conn.execute('UPDATE project_legacy SET borrowed_count = borrowed_count + 1 WHERE id = ?', (inspiration_source,))
            except Exception as e:
                print(f"Error updating borrowed count: {e}")
        
        # 通知指导老师
        advisor_name = data.get('advisor_name', '').strip()
        advisor = None
        if advisor_name:
            advisor = conn.execute('SELECT id FROM users WHERE real_name = ? AND role = ?', 
                                (advisor_name, ROLES['TEACHER'])).fetchone()
        
        if advisor:
            create_notification(conn, advisor['id'], '新项目指导申请', f"学生 {user['real_name']} 提交了新项目：{data.get('title')}，请审核", 'approval')
        
        # 通知本学院的审批者
        college_approvers = conn.execute('SELECT id FROM users WHERE college = ? AND role = ?', 
                                        (data.get('college', user['college']), ROLES['COLLEGE_APPROVER'])).fetchall()
        for approver in college_approvers:
            create_notification(conn, approver['id'], '新项目提交通知', f"本学院学生 {user['real_name']} 提交了新项目：{data.get('title')}，请关注", 'info')


        
        # 插入扩展表 (省略详细字段校验，简化处理)
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
        # 1. 负责人
        conn.execute('INSERT INTO project_members (project_id, is_leader, name, student_id, college, major, contact) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (project_id, True, user['real_name'], user['identity_number'], user['college'], data.get('major', ''), user['email'] if user['email'] else ''))
        # 2. 其他成员
        for m in data.get('members', []):
            conn.execute('INSERT INTO project_members (project_id, is_leader, name, student_id, college, major, contact) VALUES (?, ?, ?, ?, ?, ?, ?)',
                        (project_id, False, m.get('name'), m.get('student_id'), m.get('college'), m.get('major'), m.get('contact')))
                        
        conn.commit()
        return jsonify({'message': '提交成功', 'project_id': project_id})
    except Exception as e:
        conn.rollback()
        # Check if column missing error
        if 'no such column: template_type' in str(e):
             # Auto-fix schema
             try:
                 conn.execute("ALTER TABLE projects ADD COLUMN template_type TEXT DEFAULT 'default'")
                 conn.commit()
                 return jsonify({'error': '系统正在升级数据库，请重试提交'}), 500
             except:
                 pass
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/projects/<int:project_id>', methods=['GET'])
def get_project_detail(project_id):
    # REMOVED GHOST_PROJECT_IDS filtering that caused ID 1 to 9 to show as missing
    conn = get_db_connection()
    project = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    if not project:
        conn.close()
        return jsonify({'error': '未找到'}), 404
        
    res = dict(project)
    # Ensure ID matches requested ID
    res['id'] = project_id
    
    # Parse extra_info
    import json
    if res.get('extra_info'):
        try:
            res['extra_info'] = json.loads(res['extra_info'])
        except:
            res['extra_info'] = {}
    else:
        res['extra_info'] = {}
    
    # 扩展信息
    if res['project_type'] == 'innovation':
        extra = conn.execute('SELECT * FROM innovation_projects WHERE project_id = ?', (project_id,)).fetchone()
    else:
        extra = conn.execute('SELECT * FROM entrepreneurship_projects WHERE project_id = ?', (project_id,)).fetchone()
    if extra:
        extra_dict = dict(extra)
        # Prevent overwriting main project ID if extension table has an id column
        if 'id' in extra_dict:
            del extra_dict['id']
        res.update(extra_dict)
        
    # Ensure ID matches requested ID
    res['id'] = project_id
        

    # 成员
    members = conn.execute('SELECT * FROM project_members WHERE project_id = ?', (project_id,)).fetchall()
    res['members'] = [dict(m) for m in members]
    for m in res['members']:
        if m.get('is_leader'):
            if not m.get('student_id') or m.get('student_id') == '':
                u = conn.execute('SELECT identity_number FROM users WHERE id = ?', (res['created_by'],)).fetchone()
                if u and u['identity_number']:
                    m['student_id'] = u['identity_number']
            if not m.get('major') or m.get('major') == '':
                u = conn.execute('SELECT department FROM users WHERE id = ?', (res['created_by'],)).fetchone()
                if u and u['department']:
                    m['major'] = u['department']
            if not m.get('contact') or m.get('contact') == '':
                u = conn.execute('SELECT email FROM users WHERE id = ?', (res['created_by'],)).fetchone()
                if u and u['email']:
                    m['contact'] = u['email']
    
    # 评审记录
    reviews = conn.execute('''
        SELECT r.*, u.real_name as judge_name 
        FROM project_reviews r 
        JOIN users u ON r.judge_id = u.id 
        WHERE project_id = ?
    ''', (project_id,)).fetchall()
    res['reviews'] = [dict(r) for r in reviews]

    # 项目文件 (中期报告/结项报告)
    files = conn.execute('SELECT * FROM project_files WHERE project_id = ? ORDER BY created_at DESC', (project_id,)).fetchall()
    res['files'] = [dict(f) for f in files]
    
    # Borrowed Count
    legacy = conn.execute('SELECT borrowed_count FROM project_legacy WHERE original_project_id = ?', (project_id,)).fetchone()
    res['borrowed_count'] = legacy['borrowed_count'] if legacy else 0
    
    conn.close()
    return jsonify(res)

@app.route('/api/projects/<int:project_id>', methods=['PUT'])
def update_project(project_id):
    if project_id in [6, 7, 8, 9]:
        return jsonify({'error': '项目不存在'}), 404
    print(f"DEBUG: update_project called with id={project_id}")
    try:
        user_id = session.get('user_id')
        role = session.get('role')
        print(f"DEBUG: User={user_id}, Role={role}")
        
        # Allow students and approvers to edit
        allowed_roles = [ROLES['STUDENT'], ROLES['COLLEGE_APPROVER'], ROLES['SCHOOL_APPROVER'], ROLES['PROJECT_ADMIN']]
        if role not in allowed_roles:
            print(f"DEBUG: Role {role} not allowed")
            return jsonify({'error': '无权限'}), 403

        conn = get_db_connection()
        print(f"DEBUG: Checking DB for project {project_id}")
        project = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
        if not project:
            print(f"DEBUG: Project {project_id} not found in DB (Query returned None)")
            # Double check with string ID just in case
            p_str = conn.execute('SELECT * FROM projects WHERE id = ?', (str(project_id),)).fetchone()
            if p_str:
                 print(f"DEBUG: Project found using string ID! DB Type mismatch?")
            
            all_ids = conn.execute('SELECT id FROM projects').fetchall()
            print(f"DEBUG: Available IDs in DB: {[row['id'] for row in all_ids]}")
            
            conn.close()
            return jsonify({'error': '项目不存在'}), 404
        
        print(f"DEBUG: Project found: {project['title']}, CreatedBy: {project['created_by']}")
    except Exception as e:
        print(f"DEBUG: Exception in update_project prelude: {e}")
        return jsonify({'error': str(e)}), 500
    
    data = request.json
    print(f"DEBUG: Update Payload Keys: {list(data.keys())}")
    if 'title' in data: print(f"DEBUG: New Title: {data['title']}")
    if 'extra_info' in data: print(f"DEBUG: Extra Info Type: {type(data['extra_info'])}")

    # Permission checks
    if role == ROLES['STUDENT']:
        # Student: Must be creator or leader
        is_owner = (project['created_by'] == user_id)
        if not is_owner:
            # Check if user is the leader in project_members
            user_info = conn.execute('SELECT identity_number, real_name FROM users WHERE id = ?', (user_id,)).fetchone()
            is_leader = False
            
            # Check by student_id
            if user_info and user_info['identity_number']:
                member_leader = conn.execute('SELECT * FROM project_members WHERE project_id = ? AND is_leader = 1 AND student_id = ?', (project_id, user_info['identity_number'])).fetchone()
                if member_leader: is_leader = True
                else:
                    all_leaders = conn.execute('SELECT * FROM project_members WHERE project_id = ? AND is_leader = 1', (project_id,)).fetchall()
                    for l in all_leaders:
                        if l['student_id'] and l['student_id'].strip() == user_info['identity_number'].strip():
                            is_leader = True
                            break
            # Fallback: Check by name
            if not is_leader and user_info and user_info['real_name']:
                 # Try exact match
                 member_leader = conn.execute('SELECT * FROM project_members WHERE project_id = ? AND is_leader = 1 AND name = ?', (project_id, user_info['real_name'])).fetchone()
                 if member_leader: 
                     is_leader = True
                 else:
                     # Try partial/fuzzy match
                     all_leaders = conn.execute('SELECT * FROM project_members WHERE project_id = ? AND is_leader = 1', (project_id,)).fetchall()
                     for l in all_leaders:
                         if l['name'] and user_info['real_name'] in l['name']:
                             is_leader = True
                             break

            if not is_leader:
                print(f"DEBUG: Permission denied. UserID={user_id}, ProjectCreator={project['created_by']}")
                if user_info:
                    print(f"DEBUG: User Identity={user_info['identity_number']}, Name={user_info['real_name']}")
                all_leaders = conn.execute('SELECT * FROM project_members WHERE project_id = ? AND is_leader = 1', (project_id,)).fetchall()
                print(f"DEBUG: Project Leaders: {[dict(l) for l in all_leaders]}")
                
                conn.close()
                return jsonify({'error': '只能修改自己的项目'}), 403
            
        # Student: Check status
        if project['status'] not in ['pending', 'rejected', 'advisor_approved', 'college_approved']:
                conn.close()
                return jsonify({'error': '当前状态无法修改'}), 400
    
    # Approvers: Can edit any project (in their jurisdiction ideally, but simplified here)
    
    data = request.json
    import json
    extra_info_json = json.dumps(data.get('extra_info', {}))
    
    try:
        # Determine new status
        new_status = project['status']
        if role == ROLES['STUDENT']:
            # Student edits trigger re-submission logic
            new_status = 'pending'
            if project['status'] == 'school_approved':
                new_status = 'school_approved'
        # Approver edits keep the same status
        
        conn.execute('''
            UPDATE projects SET 
                title=?, leader_name=?, advisor_name=?, department=?, college=?,
                project_type=?, level=?, year=?, abstract=?, assessment_indicators=?,
                extra_info=?, status=?
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
            extra_info_json,
            new_status,
            project_id
        ))
        
        # Update extended tables
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
            
        # Update members (Delete and Re-insert simplified)
        # 1. Backup current leader info to prevent data loss
        current_leader_member = conn.execute('SELECT * FROM project_members WHERE project_id=? AND is_leader=1', (project_id,)).fetchone()
        
        conn.execute('DELETE FROM project_members WHERE project_id=?', (project_id,))
        
        # Extract leader info from multiple sources
        leader_info = data.get('extra_info', {}).get('leader_info', {})
        
        leader_name = data.get('leader_name') or leader_info.get('name')
        if not leader_name and current_leader_member:
             leader_name = current_leader_member['name']
        if not leader_name:
             leader_name = project['leader_name'] # Fallback to project table

        leader_id = data.get('leader_id') or data.get('student_id') or leader_info.get('id')
        if not leader_id and current_leader_member:
             leader_id = current_leader_member['student_id']

        leader_college = data.get('college') or leader_info.get('college')
        if not leader_college and current_leader_member: leader_college = current_leader_member['college']

        leader_major = data.get('major') or leader_info.get('major')
        if not leader_major and current_leader_member: leader_major = current_leader_member['major']
        
        leader_contact = data.get('contact') or data.get('email') or data.get('phone') or leader_info.get('email') or leader_info.get('phone') or ''
        if not leader_contact and current_leader_member:
             leader_contact = current_leader_member['contact']
        
        if not leader_contact:
             u = conn.execute('SELECT email FROM users WHERE id=?', (user_id,)).fetchone()
             if u and u['email']: leader_contact = u['email']

        print(f"DEBUG: Updating Leader - Name={leader_name}, ID={leader_id}")

        conn.execute('''
            INSERT INTO project_members (
                project_id, is_leader, name, student_id, college, major, contact
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            project_id, True, leader_name, leader_id, leader_college, leader_major, leader_contact
        ))
        # 2. Other members
        for m in data.get('members', []):
            # Avoid duplicating leader
            if m.get('student_id') and str(m.get('student_id')) == str(leader_id):
                continue
            conn.execute('INSERT INTO project_members (project_id, is_leader, name, student_id, college, major, contact) VALUES (?, ?, ?, ?, ?, ?, ?)',
                        (project_id, False, m.get('name'), m.get('student_id'), m.get('college'), m.get('major'), m.get('contact')))
                        
        conn.commit()
        return jsonify({'message': '修改成功'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/projects/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    if project_id in [6, 7, 8, 9]:
        return jsonify({'error': '项目不存在'}), 404
    role = session.get('role')
    if role not in [ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN']]:
        return jsonify({'error': '无权限'}), 403
    conn = get_db_connection()
    try:
        project = conn.execute('SELECT id FROM projects WHERE id = ?', (project_id,)).fetchone()
        if not project:
            conn.close()
            return jsonify({'error': '项目不存在'}), 404
        conn.execute('DELETE FROM projects WHERE id = ?', (project_id,))
        conn.commit()
        return jsonify({'message': '删除成功'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()
@app.route('/api/projects/<int:project_id>/audit', methods=['PUT'])
def audit_project(project_id):
    if project_id in [6, 7, 8, 9]:
        return jsonify({'error': '项目不存在'}), 404
    print(f"DEBUG: audit_project called with id={project_id}")
    role = session.get('role')
    data = request.json
    action = data.get('action') # 'approve', 'reject'
    feedback = data.get('feedback', '')
    
    conn = get_db_connection()
    project = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    
    if not project:
        print(f"DEBUG: Project {project_id} not found in DB during audit")
        conn.close()
        return jsonify({'error': '项目不存在'}), 404
        
    new_status = project['status']
    
    if role == ROLES['TEACHER']:
        # 导师审核逻辑：支持立项审核、中期审核、结项审核
        allowed_statuses = ['pending', 'midterm_submitted', 'conclusion_submitted']
        if project['status'] not in allowed_statuses:
            conn.close()
            return jsonify({'error': f'当前状态({project["status"]})无法进行指导老师审核'}), 400
        
        if action != 'approve' and not feedback:
            conn.close()
            return jsonify({'error': '驳回必须填写理由'}), 400
            
        if project['status'] == 'pending':
            new_status = 'advisor_approved' if action == 'approve' else 'rejected'
        elif project['status'] == 'midterm_submitted':
            new_status = 'midterm_advisor_approved' if action == 'approve' else 'midterm_rejected'
        elif project['status'] == 'conclusion_submitted':
            new_status = 'conclusion_advisor_approved' if action == 'approve' else 'conclusion_rejected'
        
        # 安全更新 extra_info JSON
        try:
            info = json.loads(project['extra_info']) if project['extra_info'] else {}
        except Exception:
            info = {}
            
        info['advisor_feedback'] = feedback
        if action != 'approve':
            info['rejection_level'] = '导师'
            info['rejection_reason'] = feedback
             
        conn.execute('UPDATE projects SET status = ?, extra_info = ? WHERE id = ?', (new_status, json.dumps(info), project_id))
        
        # 通知下一级或驳回通知
        if action == 'approve':
             approvers = conn.execute('SELECT id FROM users WHERE role = ? AND college = ?', 
                                    (ROLES['COLLEGE_APPROVER'], project['college'])).fetchall()
             msg_prefix = "项目"
             if "midterm" in new_status: msg_prefix = "中期报告"
             if "conclusion" in new_status: msg_prefix = "结项报告"
             
             for approver in approvers:
                create_notification(conn, approver['id'], f'{msg_prefix}待学院审批', f"{msg_prefix} {project['title']} 已由导师审核通过，请学院审批", 'approval')
        else:
             create_notification(conn, project['created_by'], '项目被导师驳回', f"您的项目 {project['title']} 被导师驳回：{feedback}", 'system')

    elif role == ROLES['COLLEGE_APPROVER']:
        # 学院审批：支持立项、中期、结项
        
        # 1. 立项阶段
        if project['status'] in ['pending', 'advisor_approved']:
            if action != 'approve' and not feedback:
                conn.close()
                return jsonify({'error': '驳回必须填写理由'}), 400
            # CHANGE: College Approve -> under_review (Wait for Expert Review)
            new_status = 'under_review' if action == 'approve' else 'rejected'
            
        # 2. 中期阶段
        elif project['status'] in ['midterm_submitted', 'midterm_advisor_approved']:
             if action != 'approve' and not feedback:
                conn.close()
                return jsonify({'error': '驳回必须填写理由'}), 400
             
             # Check Project Level
             level = project.get('project_level', 'school')
             if level in ['national', 'provincial']:
                 # National/Provincial: Go to Midterm Review
                 new_status = 'midterm_college_reviewing' if action == 'approve' else 'midterm_rejected'
             else:
                 # School: Skip College Review (Simplified) - But wait, if we are here, we are College Approver.
                 # If simplified flow (Advisor->School), College shouldn't be auditing?
                 # But if manual intervention, College can approve to College Approved.
                 new_status = 'midterm_college_approved' if action == 'approve' else 'midterm_rejected'

        # 3. 结项阶段
        elif project['status'] in ['conclusion_submitted', 'conclusion_advisor_approved']:
             if action != 'approve' and not feedback:
                conn.close()
                return jsonify({'error': '驳回必须填写理由'}), 400
             # CHANGE: Conclusion -> under_final_review
             new_status = 'under_final_review' if action == 'approve' else 'conclusion_rejected'
             
        else:
            print(f"AUDIT FAIL: College Audit Failed. ID={project_id}, Status={project['status']}, Role={role}")
            conn.close()
            return jsonify({'error': f'当前状态({project["status"]})无法进行学院审批'}), 400
        
        # Update extra_info
        try:
            info = json.loads(project['extra_info']) if project['extra_info'] else {}
        except Exception:
            info = {}
            
        if action != 'approve':
            info['rejection_level'] = '学院'
            info['rejection_reason'] = feedback
        
        if 'midterm' in project['status'] or 'midterm' in new_status:
             info['midterm_college_feedback'] = feedback
        elif 'conclusion' in project['status'] or 'conclusion' in new_status:
             info['conclusion_college_feedback'] = feedback
             
        conn.execute('UPDATE projects SET status = ?, college_feedback = ?, extra_info = ? WHERE id = ?', (new_status, feedback, json.dumps(info), project_id))
        
        if action == 'approve':
            # Notifications
            if new_status == 'under_review':
                # Notify College Admin to assign reviewers (Self notification?) or just System
                # Maybe notify Judges if auto-assigned? For now, notify Project Admin/System
                pass 
            elif new_status == 'midterm_college_reviewing':
                # Notify College Admin to assign
                pass
            elif new_status == 'under_final_review':
                # Notify School Admin to assign
                approvers = conn.execute('SELECT id FROM users WHERE role = ?', (ROLES['SCHOOL_APPROVER'],)).fetchall()
                for approver in approvers:
                    create_notification(conn, approver['id'], '结项待评审', f"项目 {project['title']} 已通过学院审核，进入结项评审阶段，请分配评委", 'approval')
            elif new_status == 'midterm_college_approved':
                approvers = conn.execute('SELECT id FROM users WHERE role = ?', (ROLES['SCHOOL_APPROVER'],)).fetchall()
                for approver in approvers:
                    create_notification(conn, approver['id'], '中期待学校审批', f"项目 {project['title']} 已通过学院审核，请学校审批", 'approval')
        else:
            create_notification(conn, project['created_by'], '项目被学院驳回', f"您的项目 {project['title']} 被学院驳回：{feedback}", 'system')
        
    elif role == ROLES['SCHOOL_APPROVER']:
        # 学校审批：支持立项、中期、结项
        # Startup: under_review (Judges done) -> school_approved
        if project['status'] == 'under_review':
             new_status = 'school_approved' if action == 'approve' else 'rejected'
             # Set Project Level
             if action == 'approve':
                 project_level = data.get('project_level', 'school')
                 conn.execute('UPDATE projects SET project_level = ? WHERE id = ?', (project_level, project_id))
                 
        elif project['status'] == 'college_approved': # Fallback for old data
             new_status = 'school_approved' if action == 'approve' else 'rejected'
             
        elif project['status'] == 'midterm_college_approved':
             new_status = 'midterm_approved' if action == 'approve' else 'midterm_rejected'
             
        elif project['status'] == 'midterm_college_reviewing': # If School overrides College Review
             new_status = 'midterm_approved' if action == 'approve' else 'midterm_rejected'
             
        elif project['status'] == 'under_final_review':
             new_status = 'finished' if action == 'approve' else 'conclusion_rejected'
             # Set Final Grade
             if action == 'approve':
                 final_grade = data.get('final_grade', '合格')
                 conn.execute('UPDATE projects SET final_grade = ? WHERE id = ?', (final_grade, project_id))
                 
        elif project['status'] == 'conclusion_college_approved': # Fallback
             new_status = 'finished' if action == 'approve' else 'conclusion_rejected'
             
        else:
            conn.close()
            return jsonify({'error': f'当前状态({project["status"]})无法进行学校审批'}), 400
        
        if action != 'approve' and not feedback:
            conn.close()
            return jsonify({'error': '驳回必须填写理由'}), 400
             
        # Update extra_info
        try:
            info = json.loads(project['extra_info']) if project['extra_info'] else {}
        except Exception:
            info = {}

        # Store stage-specific feedback
        if 'midterm' in project['status'] or 'midterm' in new_status:
             info['midterm_school_feedback'] = feedback
        elif 'conclusion' in project['status'] or 'conclusion' in new_status:
             info['conclusion_school_feedback'] = feedback
            
        if action != 'approve':
            info['rejection_level'] = '学校'
            info['rejection_reason'] = feedback
             
        conn.execute('UPDATE projects SET status = ?, school_feedback = ?, extra_info = ? WHERE id = ?', (new_status, feedback, json.dumps(info), project_id))
        
        if action == 'approve':
            if new_status == 'school_approved':
                # School Approved -> Rated (Auto or Manual?) 
                # User says: "school_approved -> rated". 
                # If "rated" is the final establishment state.
                # Let's keep it as 'school_approved' here, and maybe 'rated' is triggered by another action or just merged?
                # Actually, "rated" meant "Reviewed". Now "under_review" is reviewed.
                # So maybe school_approved IS the final state for startup?
                # User: "school_approved -> rated".
                # Okay, let's auto-transition to rated? Or keep school_approved?
                # Let's keep school_approved for now.
                create_notification(conn, project['created_by'], '立项完成', f"您的项目 {project['title']} 已完成立项评审，正式立项。", 'system')
                conn.execute('UPDATE projects SET status = "rated" WHERE id = ?', (project_id,)) # Auto move to rated
                
            elif new_status == 'midterm_approved':
                create_notification(conn, project['created_by'], '中期检查通过', f"您的项目 {project['title']} 中期检查已通过。", 'system')
            elif new_status == 'finished':
                create_notification(conn, project['created_by'], '项目已结项', f"您的项目 {project['title']} 已成功结项。", 'system')
            
            # Notify Advisor as well
            if project['advisor_name']:
                advisor = conn.execute('SELECT id FROM users WHERE real_name = ? AND role = ?', (project['advisor_name'], ROLES['TEACHER'])).fetchone()
                if advisor:
                    msg_type = "立项" if new_status == 'school_approved' else ("中期" if new_status == 'midterm_approved' else "结项")
                    create_notification(conn, advisor['id'], f'项目{msg_type}通过通知', f"您指导的项目 {project['title']} 已通过学校{msg_type}审核。", 'info')

        else:
            create_notification(conn, project['created_by'], '项目被学校驳回', f"您的项目 {project['title']} 被学校驳回：{feedback}", 'system')
            # Notify Advisor of rejection
            if project['advisor_name']:
                advisor = conn.execute('SELECT id FROM users WHERE real_name = ? AND role = ?', (project['advisor_name'], ROLES['TEACHER'])).fetchone()
                if advisor:
                    create_notification(conn, advisor['id'], '项目被学校驳回', f"您指导的项目 {project['title']} 被学校驳回：{feedback}", 'system')
        
    else:
        conn.close()
        return jsonify({'error': '无审批权限'}), 403
        
    conn.commit()
    conn.close()
    return jsonify({'message': '操作成功'})

@app.route('/api/projects/<int:project_id>/review', methods=['POST'])
def review_project(project_id):
    role = session.get('role')
    user_id = session.get('user_id')
    if role != ROLES['JUDGE']:
        return jsonify({'error': '无评审权限'}), 403
        
    data = request.json
    score = data.get('score')
    comment = data.get('comment', '').strip()
    criteria_scores = data.get('criteria_scores', {}) # JSON object
    
    try:
        score_int = int(score)
    except Exception:
        score_int = None
    if score_int is None or score_int < 0 or score_int > 100:
        return jsonify({'error': '评分必须为0-100的整数'}), 400
    if not comment:
        return jsonify({'error': '评语不能为空'}), 400
        
    conn = get_db_connection()
    
    project = conn.execute('SELECT status FROM projects WHERE id = ?', (project_id,)).fetchone()
    if not project:
        conn.close()
        return jsonify({'error': '项目不存在'}), 404
        
    # Check if assigned (optional but recommended if tasks are used)
    task = conn.execute('SELECT id FROM review_tasks WHERE project_id = ? AND judge_id = ?', (project_id, user_id)).fetchone()
    # If using task system, enforce assignment. But for compatibility, maybe allow if not strictly assigned? 
    # Let's enforce if task system is active. Since we just added it, maybe not populate yet.
    # For now, if no task exists, maybe create one or allow "open review". 
    # Requirement: "View assigned projects". So we should enforce assignment.
    # BUT for testing, we might need to auto-assign or allow open. 
    # Let's stick to: If task exists, update it. If not, just insert review (open pool mode).
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS project_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            judge_id INTEGER NOT NULL,
            score INTEGER,
            comment TEXT,
            criteria_scores TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    import json
    criteria_json = json.dumps(criteria_scores)
    
    conn.execute('INSERT INTO project_reviews (project_id, judge_id, score, comment, criteria_scores) VALUES (?, ?, ?, ?, ?)',
                (project_id, user_id, score_int, comment, criteria_json))
    
    # Update task status if exists
    if task:
        conn.execute('UPDATE review_tasks SET status = "completed" WHERE id = ?', (task['id'],))
    
    # Simple logic: If review submitted, mark project as rated (or keep school_approved if multiple judges needed)
    # For now, switch to rated to show progress
    # conn.execute('UPDATE projects SET status = "rated" WHERE id = ?', (project_id,))
    # CHANGE: Don't auto-update status. Wait for School Admin to audit.
    
    log_action(conn, user_id, 'REVIEW', f'Reviewed Project {project_id} Score: {score}', request.remote_addr)
    
    conn.commit()
    conn.close()
    return jsonify({'message': '评审提交成功'})

@app.route('/api/reviews/tasks', methods=['GET'])
def get_review_tasks():
    user_id = session.get('user_id')
    role = session.get('role')
    if role != ROLES['JUDGE']:
        return jsonify({'error': '无权限'}), 403
        
    conn = get_db_connection()
    # Join with projects to get details
    tasks = conn.execute('''
        SELECT t.*, p.title, p.project_type, p.status as project_status 
        FROM review_tasks t
        JOIN projects p ON t.project_id = p.id
        WHERE t.judge_id = ?
        ORDER BY t.created_at DESC
    ''', (user_id,)).fetchall()
    
    # Also get history (reviews table)
    history = conn.execute('''
        SELECT r.*, p.title 
        FROM project_reviews r
        JOIN projects p ON r.project_id = p.id
        WHERE r.judge_id = ?
        ORDER BY r.created_at DESC
    ''', (user_id,)).fetchall()
    
    conn.close()
    
    return jsonify({
        'tasks': [dict(t) for t in tasks],
        'history': [dict(h) for h in history]
    })

@app.route('/api/reviews/assign', methods=['POST'])
def assign_review_task():
    role = session.get('role')
    # Allow Project Admin, System Admin, College Approver (for Midterm), School Approver (for Conclusion)
    if role not in [ROLES['PROJECT_ADMIN'], ROLES['SYSTEM_ADMIN'], ROLES['COLLEGE_APPROVER'], ROLES['SCHOOL_APPROVER']]:
        return jsonify({'error': '无权限'}), 403
        
    data = request.json
    project_id = data.get('project_id')
    judge_id = data.get('judge_id')
    
    if not project_id or not judge_id:
        return jsonify({'error': '参数缺失'}), 400
        
    conn = get_db_connection()
    try:
        # Check existence
        p = conn.execute('SELECT id, status, college FROM projects WHERE id = ?', (project_id,)).fetchone()
        j = conn.execute('SELECT id FROM users WHERE id = ? AND role = ?', (judge_id, ROLES['JUDGE'])).fetchone()
        
        if not p or not j:
            return jsonify({'error': '项目或评委不存在'}), 404
            
        # Permission Check for Approvers
        if role == ROLES['COLLEGE_APPROVER']:
            # Can only assign for own college and specific statuses
            user_college = session.get('college') # Assuming college is stored in session, or query it
            # Need to get user college if not in session. session usually has user_id.
            u = conn.execute('SELECT college FROM users WHERE id = ?', (session.get('user_id'),)).fetchone()
            if not u or u['college'] != p['college']:
                return jsonify({'error': '无权分配非本学院项目'}), 403
            
            allowed = ['under_review', 'midterm_college_reviewing']
            if p['status'] not in allowed:
                return jsonify({'error': '当前状态无法由学院分配评委'}), 400
                
        if role == ROLES['SCHOOL_APPROVER']:
            # Can assign for under_final_review
            if p['status'] != 'under_final_review':
                 return jsonify({'error': '当前状态无法由学校分配评委'}), 400

        # Check duplicate
        exists = conn.execute('SELECT id FROM review_tasks WHERE project_id = ? AND judge_id = ?', (project_id, judge_id)).fetchone()
        if exists:
            return jsonify({'error': '该评委已分配此任务'}), 400
            
        conn.execute('INSERT INTO review_tasks (project_id, judge_id, status) VALUES (?, ?, "pending")', (project_id, judge_id))
        
        create_notification(conn, judge_id, '新评审任务', f'您有一个新的评审任务，项目ID: {project_id}', 'system')
        log_action(conn, session.get('user_id'), 'ASSIGN_REVIEW', f'Assigned Project {project_id} to Judge {judge_id}', request.remote_addr)
        
        conn.commit()
        return jsonify({'message': '分配成功'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# --- Legacy Library APIs ---
@app.route('/api/legacy', methods=['GET', 'POST'])
def manage_legacy():
    conn = get_db_connection()
    if request.method == 'GET':
        keyword = request.args.get('keyword', '')
        query = "SELECT * FROM project_legacy WHERE 1=1"
        params = []
        if keyword:
            query += " AND (title LIKE ? OR methodology_summary LIKE ?)"
            params.extend([f'%{keyword}%', f'%{keyword}%'])
        
        query += " ORDER BY created_at DESC"
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
        
    elif request.method == 'POST':
        # Create legacy project
        data = request.json
        try:
            conn.execute('''
                INSERT INTO project_legacy (original_project_id, title, methodology_summary, expert_comments, ppt_url)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                data.get('original_project_id'),
                data.get('title'),
                data.get('methodology_summary'),
                data.get('expert_comments'),
                data.get('ppt_url')
            ))
            conn.commit()
            return jsonify({'message': '收录成功'})
        except Exception as e:
            conn.rollback()
            return jsonify({'error': str(e)}), 500
        finally:
            conn.close()

@app.route('/api/admin/judges', methods=['GET'])
def get_all_judges():
    role = session.get('role')
    if role not in [ROLES['PROJECT_ADMIN'], ROLES['SYSTEM_ADMIN']]:
        return jsonify({'error': '无权限'}), 403
    conn = get_db_connection()
    judges = conn.execute('SELECT id, real_name, college, department FROM users WHERE role = ?', (ROLES['JUDGE'],)).fetchall()
    conn.close()
    return jsonify([dict(j) for j in judges])

@app.route('/api/admin/logs', methods=['GET'])
def get_system_logs():
    role = session.get('role')
    if role != ROLES['SYSTEM_ADMIN']:
        return jsonify({'error': '无权限'}), 403
    
    limit = request.args.get('limit', 100)
    conn = get_db_connection()
    logs = conn.execute(f'''
        SELECT l.*, u.username, u.real_name 
        FROM system_logs l
        LEFT JOIN users u ON l.user_id = u.id
        ORDER BY l.created_at DESC LIMIT {limit}
    ''').fetchall()
    conn.close()
    return jsonify([dict(l) for l in logs])

@app.route('/api/settings', methods=['GET', 'POST'])
def manage_settings():
    role = session.get('role')
    if role not in [ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN']]:
        return jsonify({'error': '无权限'}), 403
        
    conn = get_db_connection()
    if request.method == 'GET':
        settings = conn.execute('SELECT * FROM system_settings').fetchall()
        conn.close()
        return jsonify({row['key']: row['value'] for row in settings})
    else:
        data = request.json
        try:
            for key, value in data.items():
                # Check if exists
                exists = conn.execute('SELECT key FROM system_settings WHERE key = ?', (key,)).fetchone()
                if exists:
                    conn.execute('UPDATE system_settings SET value = ? WHERE key = ?', (value, key))
                else:
                    conn.execute('INSERT INTO system_settings (key, value) VALUES (?, ?)', (key, value))
            
            log_action(conn, session.get('user_id'), 'UPDATE_SETTINGS', 'Updated system settings', request.remote_addr)
            conn.commit()
            return jsonify({'message': '设置已更新'})
        except Exception as e:
            conn.rollback()
            return jsonify({'error': str(e)}), 500
        finally:
            conn.close()

@app.route('/api/projects/<int:project_id>/midterm', methods=['POST'])
def submit_midterm(project_id):
    print(f"DEBUG: submit_midterm called with id={project_id}")
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': '未登录'}), 401
    
    conn = get_db_connection()
    # Debug: Check if project exists
    check = conn.execute('SELECT id FROM projects WHERE id = ?', (project_id,)).fetchone()
    if check:
        print(f"DEBUG: Project {project_id} exists in DB")
    else:
        print(f"DEBUG: Project {project_id} NOT found in DB")
        # List all IDs for debug
        all_ids = conn.execute('SELECT id FROM projects').fetchall()
        print(f"DEBUG: Available IDs: {[r['id'] for r in all_ids]}")

    project = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    
    if not project:
        conn.close()
        return jsonify({'error': f'项目不存在 (ID: {project_id})'}), 404
        
    if project['created_by'] != user_id:
        conn.close()
        return jsonify({'error': '无权限'}), 403
        
    # 允许在中期检查相关状态提交
    if project['status'] not in ['rated', 'midterm_rejected', 'midterm_submitted']:
         conn.close()
         return jsonify({'error': '当前状态无法提交中期报告(需已立项/已评审)'}), 400
         
    data = request.json
    attachments = data.get('attachments', {}) # {report: url, achievement: url}
    
    try:
        info = json.loads(project['extra_info']) if project['extra_info'] else {}
    except:
        info = {}
        
    if 'process_materials' not in info:
        info['process_materials'] = {}
        
    info['process_materials']['midterm'] = attachments
    info['process_materials']['midterm_submitted_at'] = __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 插入 project_files 表
    for key, url in attachments.items():
        if url:
            # Check if file already exists
            existing = conn.execute('SELECT id FROM project_files WHERE project_id = ? AND file_type = ? AND file_path = ?', 
                                  (project_id, 'midterm', url)).fetchone()
            if not existing:
                filename = url.split('/')[-1]
                conn.execute('''
                    INSERT INTO project_files (project_id, file_type, file_path, original_filename, status)
                    VALUES (?, 'midterm', ?, ?, 'pending')
                ''', (project_id, url, filename))
            else:
                conn.execute('UPDATE project_files SET status = "pending" WHERE id = ?', (existing['id'],))

    conn.execute('UPDATE projects SET status = ?, extra_info = ? WHERE id = ?', ('midterm_submitted', json.dumps(info), project_id))
    
    # 通知指导老师和学院
    create_notification(conn, user_id, '中期材料提交成功', f"项目 {project['title']} 的中期材料已提交", 'system')
    
    # Notify Advisor if exists
    if project['advisor_name']:
        advisor = conn.execute('SELECT id FROM users WHERE real_name = ? AND role = ?', (project['advisor_name'], ROLES['TEACHER'])).fetchone()
        if advisor:
            create_notification(conn, advisor['id'], '中期材料待审核', f"项目 {project['title']} 提交了中期材料，请审核", 'approval')

    # Notify College Approvers
    approvers = conn.execute('SELECT id FROM users WHERE role = ? AND college = ?', (ROLES['COLLEGE_APPROVER'], project['college'])).fetchall()
    for approver in approvers:
        create_notification(conn, approver['id'], '中期材料待审核', f"项目 {project['title']} 提交了中期材料，请审核", 'approval')

    conn.commit()
    conn.close()
    return jsonify({'message': '中期材料提交成功'})

@app.route('/api/projects/<int:project_id>/conclusion', methods=['POST'])
def submit_conclusion(project_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': '未登录'}), 401
    
    conn = get_db_connection()
    project = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    
    if not project:
        conn.close()
        return jsonify({'error': '项目不存在'}), 404
        
    if project['created_by'] != user_id:
        conn.close()
        return jsonify({'error': '无权限'}), 403
        
    # 假设状态流转: midterm_approved -> conclusion_submitted
    if project['status'] not in ['midterm_approved', 'conclusion_rejected', 'conclusion_submitted']:
         conn.close()
         return jsonify({'error': '当前状态无法提交结题报告(需中期审核通过)'}), 400
         
    data = request.json
    attachments = data.get('attachments', {}) # {report: url, achievement: url}
    
    try:
        info = json.loads(project['extra_info']) if project['extra_info'] else {}
    except:
        info = {}
        
    if 'process_materials' not in info:
        info['process_materials'] = {}
        
    info['process_materials']['conclusion'] = attachments
    info['process_materials']['conclusion_submitted_at'] = __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 插入 project_files 表
    for key, url in attachments.items():
        if url:
             # Check if file already exists
            existing = conn.execute('SELECT id FROM project_files WHERE project_id = ? AND file_type = ? AND file_path = ?', 
                                  (project_id, 'conclusion', url)).fetchone()
            if not existing:
                filename = url.split('/')[-1]
                conn.execute('''
                    INSERT INTO project_files (project_id, file_type, file_path, original_filename, status)
                    VALUES (?, 'conclusion', ?, ?, 'pending')
                ''', (project_id, url, filename))
            else:
                conn.execute('UPDATE project_files SET status = "pending" WHERE id = ?', (existing['id'],))

    conn.execute('UPDATE projects SET status = ?, extra_info = ? WHERE id = ?', ('conclusion_submitted', json.dumps(info), project_id))
    
    # 通知
    create_notification(conn, user_id, '结题材料提交成功', f"项目 {project['title']} 的结题材料已提交", 'system')
    
    # Notify Advisor
    if project['advisor_name']:
        advisor = conn.execute('SELECT id FROM users WHERE real_name = ? AND role = ?', (project['advisor_name'], ROLES['TEACHER'])).fetchone()
        if advisor:
            create_notification(conn, advisor['id'], '结题材料待审核', f"项目 {project['title']} 提交了结题材料，请审核", 'approval')

    conn.commit()
    conn.close()
    return jsonify({'message': '结题材料提交成功'})

@app.route('/api/system/stats', methods=['GET'])
def system_stats():
    conn = get_db_connection()
    try:
        # 1. Status Distribution
        status_stats = conn.execute('SELECT status, COUNT(*) as count FROM projects WHERE id NOT IN (6, 7, 8, 9) GROUP BY status').fetchall()
        
        # 2. Role Distribution
        role_stats = conn.execute('SELECT role, COUNT(*) as count FROM users GROUP BY role').fetchall()
        
        # 3. College Distribution (Projects)
        college_stats = conn.execute('SELECT college, COUNT(*) as count FROM projects WHERE id NOT IN (6, 7, 8, 9) GROUP BY college').fetchall()
        
        # 4. Project Type Distribution
        type_stats = conn.execute('SELECT project_type, COUNT(*) as count FROM projects WHERE id NOT IN (6, 7, 8, 9) GROUP BY project_type').fetchall()
        
    except sqlite3.OperationalError:
        status_stats = []
        role_stats = []
        college_stats = []
        type_stats = []
        
    conn.close()
    
    return jsonify({
        'project_stats': [dict(row) for row in status_stats],
        'user_stats': [dict(row) for row in role_stats],
        'college_stats': [dict(row) for row in college_stats],
        'type_stats': [dict(row) for row in type_stats]
    })

@app.route('/api/reports/export', methods=['GET'])
def export_projects():
    user_id = session.get('user_id')
    role = session.get('role')
    
    if not user_id:
        return jsonify({'error': '未登录'}), 401
        
    # Re-use logic from get_projects or simplify for export
    # For simplicity, we export what the user can see.
    # But usually exports are for admins. Let's allow admins and approvers.
    if role not in [ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN'], ROLES['SCHOOL_APPROVER'], ROLES['COLLEGE_APPROVER']]:
         return jsonify({'error': '无导出权限'}), 403

    conn = get_db_connection()
    query = "SELECT * FROM projects WHERE 1=1"
    params = []
    
    if role == ROLES['COLLEGE_APPROVER']:
        current_user = conn.execute('SELECT college FROM users WHERE id = ?', (user_id,)).fetchone()
        if current_user:
            query += " AND college = ?"
            params.append(current_user['college'])
            
    query += " AND id NOT IN (6, 7, 8, 9) ORDER BY created_at DESC"
    
    projects = conn.execute(query, params).fetchall()
    conn.close()
    
    # Generate CSV
    import io
    import csv
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Headers
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

@app.route('/api/backups/<path:filename>', methods=['GET'])
def download_backup(filename):
    role = session.get('role')
    if role != ROLES['SYSTEM_ADMIN']:
        return jsonify({'error': '无权限'}), 403
    base_dir = os.path.dirname(os.path.abspath(__file__))
    backups_dir = os.path.join(base_dir, 'backups')
    full_path = os.path.join(backups_dir, filename)
    if not os.path.exists(full_path):
        return jsonify({'error': '文件不存在'}), 404
    return send_from_directory(backups_dir, filename, as_attachment=True)

# --- 通知相关 ---
@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': '未登录'}), 401
    
    conn = get_db_connection()
    # 获取所有通知
    notifications = conn.execute('SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC', (user_id,)).fetchall()
    conn.close()
    return jsonify([dict(row) for row in notifications])

@app.route('/api/notifications/<int:nid>/read', methods=['PUT'])
def read_notification(nid):
    user_id = session.get('user_id')
    conn = get_db_connection()
    conn.execute('UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?', (nid, user_id))
    conn.commit()
    conn.close()
    return jsonify({'message': '已读'})

# --- 文件上传与阶段管理 (中期/结项) ---
@app.route('/api/projects/<int:pid>/files', methods=['POST'])
def upload_file(pid):
    # 这里模拟文件上传，实际应保存文件到 disk
    user_id = session.get('user_id')
    role = session.get('role')
    
    if not user_id: return jsonify({'error': '未登录'}), 401
    
    data = request.json
    file_type = data.get('file_type') # midterm, conclusion
    file_name = data.get('file_name')
    # 模拟路径
    file_path = f"/uploads/{pid}/{file_type}/{file_name}"
    
    conn = get_db_connection()
    project = conn.execute('SELECT * FROM projects WHERE id = ?', (pid,)).fetchone()
    
    if not project:
        conn.close()
        return jsonify({'error': '项目不存在'}), 404
        
    # 插入文件记录
    conn.execute('''
        INSERT INTO project_files (project_id, file_type, file_path, original_filename, status)
        VALUES (?, ?, ?, ?, 'pending')
    ''', (pid, file_type, file_path, file_name))
    
    # 更新项目状态
    new_status = project['status']
    if file_type == 'midterm':
        new_status = 'midterm_submitted'
    elif file_type == 'conclusion':
        new_status = 'conclusion_submitted'
        
    if new_status != project['status']:
        conn.execute('UPDATE projects SET status = ? WHERE id = ?', (new_status, pid))
        
        # 通知指导老师
        advisor = conn.execute('SELECT id FROM users WHERE real_name = ? AND role = ?', 
                              (project['advisor_name'], ROLES['TEACHER'])).fetchone()
        
        if advisor:
             create_notification(conn, advisor['id'], '新的项目文件提交', f"项目 {project['title']} 提交了 {file_type} 文件，请审核", 'approval')
        else:
             # 如果没有导师，通知学院审批者
             approvers = conn.execute('SELECT id FROM users WHERE role = ? AND college = ?', 
                                    (ROLES['COLLEGE_APPROVER'], project['college'])).fetchall()
             for approver in approvers:
                create_notification(conn, approver['id'], '新的项目文件提交', f"项目 {project['title']} 提交了 {file_type} 文件，请审核", 'approval')
        
    conn.commit()
    conn.close()
    return jsonify({'message': '提交成功'})

@app.route('/api/projects/<int:pid>/files/audit', methods=['PUT'])
def audit_file(pid):
    # 审核中期/结项报告
    role = session.get('role')
    data = request.json
    file_type = data.get('file_type')
    action = data.get('action') # approve, reject
    feedback = data.get('feedback', '')
    
    conn = get_db_connection()
    project = conn.execute('SELECT * FROM projects WHERE id = ?', (pid,)).fetchone()
    if not project:
        conn.close()
        return jsonify({'error': '项目不存在'}), 404

    current_status = project['status']
    new_status = current_status
    
    # 定义状态流转逻辑
    # 提交(submitted) -> 导师审(advisor_approved) -> 学院审(college_approved) -> 学校审(approved/finished)
    
    if role == ROLES['TEACHER']:
        if current_status not in ['midterm_submitted', 'conclusion_submitted']:
             conn.close()
             return jsonify({'error': '当前状态无法进行指导老师审核'}), 400
             
        suffix = 'college_approved' if action == 'approve' else 'rejected'
        new_status = f"{file_type}_{suffix}"
        
        if action == 'approve':
             # Logic Change:
             # If Midterm & School Level -> Skip College (midterm_college_approved) -> Notify School
             # If Midterm & Nat/Prov -> midterm_advisor_approved -> Notify College
             # If Conclusion -> conclusion_advisor_approved -> Notify College
             
             level = project.get('project_level', 'school')
             
             if file_type == 'midterm':
                 if level in ['national', 'provincial']:
                     new_status = 'midterm_advisor_approved'
                     # Notify College
                     approvers = conn.execute('SELECT id FROM users WHERE role = ? AND college = ?', (ROLES['COLLEGE_APPROVER'], project['college'])).fetchall()
                     for approver in approvers:
                        create_notification(conn, approver['id'], '中期报告待审批', f"项目 {project['title']} 已通过导师审核，请学院审批", 'approval')
                 else:
                     # School Level: Skip College
                     new_status = 'midterm_college_approved'
                     approvers = conn.execute('SELECT id FROM users WHERE role = ?', (ROLES['SCHOOL_APPROVER'],)).fetchall()
                     for approver in approvers:
                        create_notification(conn, approver['id'], '中期报告待审批', f"项目 {project['title']} 已通过导师审核（校级简化流程），请学校审批", 'approval')
             elif file_type == 'conclusion':
                 # Always go to College first for Conclusion
                 new_status = 'conclusion_advisor_approved'
                 approvers = conn.execute('SELECT id FROM users WHERE role = ? AND college = ?', (ROLES['COLLEGE_APPROVER'], project['college'])).fetchall()
                 for approver in approvers:
                    create_notification(conn, approver['id'], '结项报告待审批', f"项目 {project['title']} 已通过导师审核，请学院审批", 'approval')

    elif role == ROLES['COLLEGE_APPROVER']:
        # 允许审核 advisor_approved 状态
        # 如果没有导师，可能直接是 submitted (但在 upload_file 中如果无导师通知了学院，这里也要兼容 submitted)
        allowed_statuses = [f"{file_type}_advisor_approved", f"{file_type}_submitted"]
        if current_status not in allowed_statuses:
             conn.close()
             return jsonify({'error': '当前状态无法进行学院审核'}), 400
             
        # Logic Change:
        # Midterm -> midterm_college_reviewing (if nat/prov) or midterm_college_approved (if school - but school skipped college usually)
        # Conclusion -> under_final_review
        
        if action == 'approve':
            if file_type == 'midterm':
                 level = project.get('project_level', 'school')
                 if level in ['national', 'provincial']:
                     new_status = 'midterm_college_reviewing'
                     # Notify College Admin to assign reviewers? Or just stay silent until assigned?
                 else:
                     new_status = 'midterm_college_approved'
                     approvers = conn.execute('SELECT id FROM users WHERE role = ?', (ROLES['SCHOOL_APPROVER'],)).fetchall()
                     for approver in approvers:
                        create_notification(conn, approver['id'], '中期报告待审批', f"项目 {project['title']} 已通过学院审核，请学校审批", 'approval')
            elif file_type == 'conclusion':
                new_status = 'under_final_review'
                approvers = conn.execute('SELECT id FROM users WHERE role = ?', (ROLES['SCHOOL_APPROVER'],)).fetchall()
                for approver in approvers:
                    create_notification(conn, approver['id'], '结项待评审', f"项目 {project['title']} 已通过学院审核，进入结项评审阶段，请分配评委", 'approval')
        else:
            new_status = f"{file_type}_rejected"

    elif role == ROLES['SCHOOL_APPROVER']:
        # School Approver handles:
        # Midterm: midterm_college_approved (from School Level) or midterm_college_reviewing (override) -> midterm_approved
        # Conclusion: under_final_review -> finished
        
        allowed_statuses = [f"{file_type}_college_approved", 'midterm_college_reviewing', 'under_final_review']
        if current_status not in allowed_statuses:
             conn.close()
             return jsonify({'error': '当前状态无法进行学校审核'}), 400
             
        if action != 'approve' and not feedback:
             conn.close()
             return jsonify({'error': '驳回必须填写理由'}), 400
             
        if action == 'approve':
            if file_type == 'midterm':
                new_status = 'midterm_approved'
                create_notification(conn, project['created_by'], '中期检查通过', f"您的中期报告已通过学校审核。", 'system')
            elif file_type == 'conclusion':
                new_status = 'finished'
                # Set Final Grade
                final_grade = data.get('final_grade', '合格')
                conn.execute('UPDATE projects SET final_grade = ? WHERE id = ?', (final_grade, pid))
                create_notification(conn, project['created_by'], '项目已结项', f"您的项目已成功结项。", 'system')
        else:
            new_status = f"{file_type}_rejected"
            create_notification(conn, project['created_by'], '项目材料被驳回', 
                              f"您的 {file_type} 被学校驳回。{feedback}", 'system')

    else:
        conn.close()
        return jsonify({'error': '无审批权限'}), 403

    # 更新文件状态
    conn.execute('UPDATE project_files SET status = ? WHERE project_id = ? AND file_type = ?', 
                (action + 'd', pid, file_type))
    
    # 更新项目状态
    conn.execute('UPDATE projects SET status = ?, school_feedback = ? WHERE id = ?', (new_status, feedback, pid))
    
    # 如果是驳回，可能需要更复杂的逻辑（如允许重新提交），这里简化为状态变更，upload_file需允许在 rejected 状态下上传
    
    conn.commit()
    conn.close()
    return jsonify({'message': '审核完成'})

@app.route('/api/common/upload', methods=['POST'])
def common_upload():
    if 'file' not in request.files:
        return jsonify({'error': '未上传文件'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '文件名为空'}), 400
        
    if file:
        # Generate a safe filename using timestamp and UUID to avoid encoding issues with Chinese filenames
        import time
        import uuid
        ext = os.path.splitext(file.filename)[1]
        filename = f"{int(time.time())}_{uuid.uuid4().hex[:8]}{ext}"
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Return the URL for the file
        return jsonify({
            'message': '上传成功', 
            'url': f'/static/uploads/{filename}',
            'filename': filename
        })
    return jsonify({'error': '上传失败'}), 500

    
    # 统计用户角色
    role_stats = conn.execute('SELECT role, COUNT(*) as count FROM users GROUP BY role').fetchall()
    
    conn.close()
    
    return jsonify({
        'project_stats': [dict(row) for row in status_stats],
        'user_stats': [dict(row) for row in role_stats]
    })

@app.route('/api/system/backup', methods=['POST'])
def system_backup():
    role = session.get('role')
    if role != ROLES['SYSTEM_ADMIN']:
        return jsonify({'error': '无权限'}), 403
        
    import os, shutil
    from datetime import datetime
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        src = os.path.join(base_dir, 'database.db')
        if not os.path.exists(src):
            return jsonify({'error': '数据库文件不存在'}), 500
        backups_dir = os.path.join(base_dir, 'backups')
        os.makedirs(backups_dir, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d-%H%M%S')
        dst = os.path.join(backups_dir, f'database-{ts}.db')
        shutil.copyfile(src, dst)
        return jsonify({'message': f'备份成功: {os.path.basename(dst)}', 'path': f'/api/backups/{os.path.basename(dst)}'})
    except Exception as e:
        return jsonify({'error': f'备份失败: {str(e)}'}), 500

# --- 公告/新闻管理 ---

@app.route('/api/announcements', methods=['GET'])
def get_announcements():
    conn = get_db_connection()
    try:
        announcements = conn.execute('''
            SELECT a.*, u.real_name as author_name 
            FROM announcements a 
            LEFT JOIN users u ON a.created_by = u.id 
            ORDER BY a.created_at DESC
        ''').fetchall()
    except sqlite3.OperationalError:
        announcements = []
    conn.close()
    return jsonify([dict(row) for row in announcements])

@app.route('/api/announcements', methods=['POST'])
def create_announcement():
    user_id = session.get('user_id')
    role = session.get('role')
    
    if role not in [ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN']]:
        return jsonify({'error': '无权限'}), 403
        
    data = request.json
    conn = get_db_connection()
    try:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT,
                type TEXT DEFAULT 'news',
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.execute('''
            INSERT INTO announcements (title, content, type, created_by)
            VALUES (?, ?, ?, ?)
        ''', (data.get('title'), data.get('content'), data.get('type', 'news'), user_id))
        
        users = conn.execute('SELECT id FROM users WHERE id != ?', (user_id,)).fetchall()
        for u in users:
            create_notification(conn, u['id'], '新公告发布', f"系统发布了新公告：{data.get('title')}", 'info')
            
        conn.commit()
        return jsonify({'message': '发布成功'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/announcements/<int:aid>', methods=['DELETE'])
def delete_announcement(aid):
    role = session.get('role')
    if role not in [ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN']]:
        return jsonify({'error': '无权限'}), 403
        
    conn = get_db_connection()
    conn.execute('DELETE FROM announcements WHERE id = ?', (aid,))
    conn.commit()
    conn.close()
    return jsonify({'message': '删除成功'})

# --- 赛事管理 (Competitions) ---

@app.route('/api/competitions', methods=['GET'])
def get_competitions():
    conn = get_db_connection()
    # 简单的状态排序：active > upcoming > ended
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
    except sqlite3.OperationalError:
        competitions = []
    
    # Check if student is registered for each competition
    user_id = session.get('user_id')
    res = [dict(row) for row in competitions]
    
    if user_id and session.get('role') == ROLES['STUDENT']:
        user_projects = conn.execute('SELECT competition_id, id, status FROM projects WHERE created_by = ? AND competition_id IS NOT NULL AND id NOT IN (6, 7, 8, 9)', (user_id,)).fetchall()
        project_map = {row['competition_id']: {'id': row['id'], 'status': row['status']} for row in user_projects}
        
        for comp in res:
            if comp['id'] in project_map:
                comp['is_registered'] = True
                comp['project_id'] = project_map[comp['id']]['id']
                comp['project_status'] = project_map[comp['id']]['status']
            else:
                comp['is_registered'] = False
            
    conn.close()
    return jsonify(res)

@app.route('/api/competitions', methods=['POST'])
def create_competition():
    role = session.get('role')
    if role not in [ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN']]:
        return jsonify({'error': '无权限'}), 403
        
    data = request.json
    conn = get_db_connection()
    try:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS competitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                level TEXT,
                organizer TEXT,
                registration_start DATE,
                registration_end DATE,
                description TEXT,
                status TEXT DEFAULT 'active',
                template_type TEXT DEFAULT 'default',
                form_config TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Check if form_config column exists (for existing table)
        try:
            conn.execute('SELECT form_config FROM competitions LIMIT 1')
        except sqlite3.OperationalError:
            conn.execute('ALTER TABLE competitions ADD COLUMN form_config TEXT')

        # Check if template_type column exists (for existing table)
        try:
            conn.execute('SELECT template_type FROM competitions LIMIT 1')
        except sqlite3.OperationalError:
            conn.execute("ALTER TABLE competitions ADD COLUMN template_type TEXT DEFAULT 'default'")
        
        import json
        form_config = json.dumps(data.get('form_config', {})) if data.get('form_config') else None

        conn.execute('''
            INSERT INTO competitions (title, level, organizer, registration_start, registration_end, description, status, template_type, form_config)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('title'),
            data.get('level', 'School'),
            data.get('organizer'),
            data.get('registration_start'),
            data.get('registration_end'),
            data.get('description'),
            data.get('status', 'active'),
            data.get('template_type', 'default'),
            form_config
        ))
        conn.commit()
        return jsonify({'message': '赛事发布成功'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/competitions/<int:cid>', methods=['PUT'])
def update_competition(cid):
    role = session.get('role')
    if role not in [ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN']]:
        return jsonify({'error': '无权限'}), 403
        
    data = request.json
    conn = get_db_connection()
    try:
        import json
        form_config = json.dumps(data.get('form_config', {})) if data.get('form_config') else None
        
        conn.execute('''
            UPDATE competitions 
            SET title=?, level=?, organizer=?, registration_start=?, registration_end=?, description=?, status=?, template_type=?, form_config=?
            WHERE id=?
        ''', (
            data.get('title'),
            data.get('level'),
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
        return jsonify({'message': '更新成功'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/competitions/<int:cid>', methods=['DELETE'])
def delete_competition(cid):
    role = session.get('role')
    if role not in [ROLES['SYSTEM_ADMIN'], ROLES['PROJECT_ADMIN']]:
        return jsonify({'error': '无权限'}), 403
        
    conn = get_db_connection()
    conn.execute('DELETE FROM competitions WHERE id = ?', (cid,))
    conn.commit()
    conn.close()
    return jsonify({'message': '删除成功'})


@app.errorhandler(404)
def page_not_found(e):
    print(f"DEBUG: 404 Error on request: {request.method} {request.path}")
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Resource not found', 'path': request.path}), 404
    return "404 Not Found", 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)
