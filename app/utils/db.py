import sqlite3
from flask import g
from config import get_config
import os
from werkzeug.security import generate_password_hash

config = get_config()

def get_db_connection():
    if 'db' not in g:
        g.db = sqlite3.connect(config.DB_PATH, timeout=10)
        g.db.row_factory = sqlite3.Row
        try:
            g.db.execute('PRAGMA journal_mode=WAL')
            g.db.execute('PRAGMA synchronous=NORMAL')
            g.db.execute('PRAGMA foreign_keys=ON')
            g.db.execute('PRAGMA busy_timeout=5000')
        except Exception:
            pass
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """初始化数据库，根据 schema.sql 创建表并插入预设数据"""
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
    
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # 从 schema.sql 执行建表语句
    schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'schema.sql')
    with open(schema_path, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    
    # 初始化预设数据
    users = [
        ('admin', 'admin123', 'system_admin', '系统管理员', '', ''),
        ('proj_admin', 'admin123', 'project_admin', '教务处老师', '', ''),
        ('col_approver', 'admin123', 'college_approver', '学院书记', '计算机学院（人工智能学院）', '学院办公室'),
        ('sch_approver', 'admin123', 'school_approver', '校领导', '', ''),
        ('judge1', 'admin123', 'judge', '王教授', '', ''),
        ('teacher1', 'teacher123', 'teacher', '张老师', '计算机学院（人工智能学院）', '计算机科学与技术'),
        ('student1', 'student123', 'student', '李同学', '计算机学院（人工智能学院）', '软件工程')
    ]

    for u in users:
        conn.execute('''
            INSERT INTO users (username, password, role, real_name, identity_number, status, college, department) 
            VALUES (?, ?, ?, ?, '000000', 'active', ?, ?)
        ''', (u[0], generate_password_hash(u[1]), u[2], u[3], u[4], u[5]))

    conn.commit()
    conn.close()
    print("Database initialized successfully from schema.sql.")

def ensure_db_schema():
    if not os.path.exists(config.DB_PATH):
        return

    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cols = [r[1] for r in conn.execute('PRAGMA table_info(users)').fetchall()]
        if 'email' not in cols:
            conn.execute('ALTER TABLE users ADD COLUMN email TEXT')
        if 'phone' not in cols:
            conn.execute('ALTER TABLE users ADD COLUMN phone TEXT')
        if 'college' not in cols:
            conn.execute('ALTER TABLE users ADD COLUMN college TEXT')
        if 'department' not in cols:
            conn.execute('ALTER TABLE users ADD COLUMN department TEXT')
        if 'personal_info' not in cols:
            conn.execute('ALTER TABLE users ADD COLUMN personal_info TEXT')
        if 'teaching_office' not in cols:
            conn.execute('ALTER TABLE users ADD COLUMN teaching_office TEXT')
        if 'research_area' not in cols:
            conn.execute('ALTER TABLE users ADD COLUMN research_area TEXT')
        if 'status' not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'active'")

        # Competitions table schema updates
        comp_cols = [r[1] for r in conn.execute('PRAGMA table_info(competitions)').fetchall()]
        if 'system_type' not in comp_cols:
            conn.execute("ALTER TABLE competitions ADD COLUMN system_type TEXT")
        if 'competition_level' not in comp_cols:
            conn.execute("ALTER TABLE competitions ADD COLUMN competition_level TEXT")
        if 'national_organizer' not in comp_cols:
            conn.execute("ALTER TABLE competitions ADD COLUMN national_organizer TEXT")
        if 'school_organizer' not in comp_cols:
            conn.execute("ALTER TABLE competitions ADD COLUMN school_organizer TEXT")

        project_cols = [r[1] for r in conn.execute('PRAGMA table_info(projects)').fetchall()]
        if 'linked_project_id' not in project_cols:
            conn.execute('ALTER TABLE projects ADD COLUMN linked_project_id INTEGER')
        if 'review_stage' not in project_cols:
            conn.execute('ALTER TABLE projects ADD COLUMN review_stage TEXT')
        if 'college_review_result' not in project_cols:
            conn.execute('ALTER TABLE projects ADD COLUMN college_review_result TEXT')
        if 'school_review_result' not in project_cols:
            conn.execute('ALTER TABLE projects ADD COLUMN school_review_result TEXT')
        if 'provincial_award_level' not in project_cols:
            conn.execute('ALTER TABLE projects ADD COLUMN provincial_award_level TEXT')
        if 'national_award_level' not in project_cols:
            conn.execute('ALTER TABLE projects ADD COLUMN national_award_level TEXT')
        if 'research_admin_opinion' not in project_cols:
            conn.execute('ALTER TABLE projects ADD COLUMN research_admin_opinion TEXT')
        if 'department_head_opinion' not in project_cols:
            conn.execute('ALTER TABLE projects ADD COLUMN department_head_opinion TEXT')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS project_upgrade_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                applicant_id INTEGER NOT NULL,
                from_level TEXT,
                to_level TEXT,
                status TEXT DEFAULT 'pending',
                reason TEXT,
                reviewer_id INTEGER,
                review_comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
                FOREIGN KEY (applicant_id) REFERENCES users (id),
                FOREIGN KEY (reviewer_id) REFERENCES users (id)
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS project_awards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                stage TEXT NOT NULL,
                award_level TEXT NOT NULL,
                award_name TEXT,
                award_time TEXT,
                issuer TEXT,
                created_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS process_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_name TEXT NOT NULL UNIQUE,
                process_structure TEXT NOT NULL,
                has_mid_check BOOLEAN NOT NULL,
                has_final_acceptance BOOLEAN NOT NULL
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS process_node_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER NOT NULL,
                node_name TEXT NOT NULL,
                status_options TEXT NOT NULL,
                UNIQUE(template_id, node_name),
                FOREIGN KEY (template_id) REFERENCES process_templates(id)
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS award_levels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER NOT NULL UNIQUE,
                level_options TEXT NOT NULL,
                FOREIGN KEY (template_id) REFERENCES process_templates(id)
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS project_node_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                node_name TEXT NOT NULL,
                current_status TEXT,
                comment TEXT,
                award_level TEXT,
                updated_by INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(project_id, node_name),
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (updated_by) REFERENCES users(id)
            )
        ''')
        
        # Add column if not exists
        try:
            conn.execute('ALTER TABLE project_node_status ADD COLUMN award_level TEXT')
        except sqlite3.OperationalError:
            pass

        conn.execute('''
            INSERT OR IGNORE INTO process_templates (template_name, process_structure, has_mid_check, has_final_acceptance) VALUES
            ('大挑', '["学院赛","校赛","省赛","国赛"]', 0, 0),
            ('大创创新训练', '["项目申报","学院评审","学校立项","项目实施","中期检查","结题验收"]', 1, 1),
            ('国创赛', '["校赛","省赛","国赛"]', 0, 0),
            ('小挑', '["校赛","省赛","国赛"]', 0, 0),
            ('大创创业训练', '["项目申报","学院评审","学校立项","项目实施","中期检查","结题验收"]', 1, 1),
            ('大创创业实践', '["项目申报","学院评审","学校立项","项目实施","中期检查","结题验收"]', 1, 1),
            ('三创赛常规赛', '["校赛","省赛","国赛"]', 0, 0),
            ('三创赛实战赛', '["校赛","省赛","国赛"]', 0, 0)
        ''')

        conn.execute('''
            INSERT OR IGNORE INTO process_node_status (template_id, node_name, status_options)
            SELECT id, '学院赛', '["待评审","已推荐","未推荐"]' FROM process_templates WHERE template_name = '大挑'
        ''')
        conn.execute('''
            INSERT OR IGNORE INTO process_node_status (template_id, node_name, status_options)
            SELECT id, '校赛', '["待评审","已推荐","未推荐"]' FROM process_templates WHERE template_name = '大挑'
        ''')
        conn.execute('''
            INSERT OR IGNORE INTO process_node_status (template_id, node_name, status_options)
            SELECT id, '省赛', '["待评审","已晋级","未晋级"]' FROM process_templates WHERE template_name = '大挑'
        ''')
        conn.execute('''
            INSERT OR IGNORE INTO process_node_status (template_id, node_name, status_options)
            SELECT id, '国赛', '["待评审","已获奖","未获奖"]' FROM process_templates WHERE template_name = '大挑'
        ''')

        conn.execute('''
            INSERT OR IGNORE INTO process_node_status (template_id, node_name, status_options)
            SELECT id, '校赛', '["待评审","已推荐","未推荐"]' FROM process_templates
            WHERE template_name IN ('国创赛','小挑','三创赛常规赛','三创赛实战赛')
        ''')
        conn.execute('''
            INSERT OR IGNORE INTO process_node_status (template_id, node_name, status_options)
            SELECT id, '省赛', '["待评审","已晋级","未晋级"]' FROM process_templates
            WHERE template_name IN ('国创赛','小挑','三创赛常规赛','三创赛实战赛')
        ''')
        conn.execute('''
            INSERT OR IGNORE INTO process_node_status (template_id, node_name, status_options)
            SELECT id, '国赛', '["待评审","已获奖","未获奖"]' FROM process_templates
            WHERE template_name IN ('国创赛','小挑','三创赛常规赛','三创赛实战赛')
        ''')

        conn.execute('''
            INSERT OR IGNORE INTO process_node_status (template_id, node_name, status_options)
            SELECT id, '项目申报', '["待导师审核","导师通过","导师驳回"]' FROM process_templates
            WHERE template_name IN ('大创创新训练','大创创业训练','大创创业实践')
        ''')
        conn.execute('''
            INSERT OR IGNORE INTO process_node_status (template_id, node_name, status_options)
            SELECT id, '学院评审', '["待评审","通过","驳回"]' FROM process_templates
            WHERE template_name IN ('大创创新训练','大创创业训练','大创创业实践')
        ''')
        conn.execute('''
            INSERT OR IGNORE INTO process_node_status (template_id, node_name, status_options)
            SELECT id, '学校立项', '["待立项","已立项","驳回"]' FROM process_templates
            WHERE template_name IN ('大创创新训练','大创创业训练','大创创业实践')
        ''')
        conn.execute('''
            INSERT OR IGNORE INTO process_node_status (template_id, node_name, status_options)
            SELECT id, '项目实施', '["进行中","已完成"]' FROM process_templates
            WHERE template_name IN ('大创创新训练','大创创业训练','大创创业实践')
        ''')
        conn.execute('''
            INSERT OR IGNORE INTO process_node_status (template_id, node_name, status_options)
            SELECT id, '中期检查', '["待提交","待审核","通过","需整改","不通过"]' FROM process_templates
            WHERE template_name IN ('大创创新训练','大创创业训练','大创创业实践')
        ''')
        conn.execute('''
            INSERT OR IGNORE INTO process_node_status (template_id, node_name, status_options)
            SELECT id, '结题验收', '["待提交","待审核","通过","不通过"]' FROM process_templates
            WHERE template_name IN ('大创创新训练','大创创业训练','大创创业实践')
        ''')

        conn.execute('''
            INSERT OR REPLACE INTO award_levels (template_id, level_options)
            SELECT id, '["特等奖","一等奖","二等奖","三等奖"]' FROM process_templates WHERE template_name = '大挑'
        ''')
        conn.execute('''
            INSERT OR REPLACE INTO award_levels (template_id, level_options)
            SELECT id, '["金奖","银奖","铜奖"]' FROM process_templates WHERE template_name IN ('国创赛','小挑')
        ''')
        conn.execute('''
            INSERT OR REPLACE INTO award_levels (template_id, level_options)
            SELECT id, '["特等奖","一等奖","二等奖","三等奖"]' FROM process_templates WHERE template_name IN ('三创赛常规赛','三创赛实战赛')
        ''')

        # Update review_tasks
        try:
            conn.execute('ALTER TABLE review_tasks ADD COLUMN review_level TEXT DEFAULT "college"')
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute('ALTER TABLE review_tasks ADD COLUMN team_id INTEGER')
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute('ALTER TABLE review_tasks ADD COLUMN score INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute('ALTER TABLE review_tasks ADD COLUMN comments TEXT')
        except sqlite3.OperationalError:
            pass

        # Create review_scores table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS review_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                criteria TEXT NOT NULL,
                score INTEGER NOT NULL,
                max_score INTEGER NOT NULL,
                FOREIGN KEY (task_id) REFERENCES review_tasks(id) ON DELETE CASCADE
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS review_teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                level TEXT NOT NULL,
                college TEXT,
                discipline_group TEXT,
                leader_user_id INTEGER,
                enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, level),
                FOREIGN KEY (leader_user_id) REFERENCES users(id)
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS review_team_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role_in_team TEXT DEFAULT 'member',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(team_id, user_id),
                FOREIGN KEY (team_id) REFERENCES review_teams(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

        # Update projects table
        try:
            conn.execute('ALTER TABLE projects ADD COLUMN college_avg_score REAL')
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute('ALTER TABLE projects ADD COLUMN school_avg_score REAL')
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute('ALTER TABLE projects ADD COLUMN college_rank INTEGER')
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute('ALTER TABLE projects ADD COLUMN school_rank INTEGER')
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute('ALTER TABLE projects ADD COLUMN current_level TEXT DEFAULT "college"')
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute('ALTER TABLE projects ADD COLUMN provincial_status TEXT')
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute('ALTER TABLE projects ADD COLUMN provincial_certificate_no TEXT')
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute('ALTER TABLE projects ADD COLUMN provincial_advance_national INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute('ALTER TABLE projects ADD COLUMN provincial_review_comment TEXT')
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute('ALTER TABLE projects ADD COLUMN national_status TEXT')
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute('ALTER TABLE projects ADD COLUMN national_certificate_no TEXT')
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute('ALTER TABLE projects ADD COLUMN national_review_comment TEXT')
        except sqlite3.OperationalError:
            pass

        default_password = 'Test123456'
        hp = generate_password_hash(default_password)
        def ensure_user(username, role, real_name, college=None, department=None):
            rows = conn.execute('SELECT id FROM users WHERE username = ? ORDER BY id ASC', (username,)).fetchall()
            if rows:
                keep_id = rows[0]['id']
                extra_ids = [r['id'] for r in rows[1:]]
                for other_id in extra_ids:
                    conn.execute('UPDATE review_tasks SET judge_id = ? WHERE judge_id = ?', (keep_id, other_id))

                    tm = conn.execute('SELECT team_id FROM review_team_members WHERE user_id = ?', (other_id,)).fetchall()
                    for r in tm:
                        team_id = r['team_id']
                        exists = conn.execute(
                            'SELECT id FROM review_team_members WHERE team_id = ? AND user_id = ?',
                            (team_id, keep_id)
                        ).fetchone()
                        if exists:
                            conn.execute('DELETE FROM review_team_members WHERE team_id = ? AND user_id = ?', (team_id, other_id))
                        else:
                            conn.execute('UPDATE review_team_members SET user_id = ? WHERE team_id = ? AND user_id = ?', (keep_id, team_id, other_id))

                    conn.execute('DELETE FROM users WHERE id = ?', (other_id,))

                conn.execute(
                    'UPDATE users SET role = ?, password = ?, real_name = COALESCE(real_name, ?), college = COALESCE(college, ?), department = COALESCE(department, ?), status = COALESCE(status, ?) WHERE id = ?',
                    (role, hp, real_name, college, department, 'active', keep_id)
                )
                return keep_id
            conn.execute(
                'INSERT INTO users (username, password, role, real_name, college, department, status) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (username, hp, role, real_name, college, department, 'active')
            )
            return conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()['id']

        cs_college = '计算机学院'
        college_admin_id = ensure_user('test_college_admin_cs', 'college_approver', '【测试】计算机学院管理员', cs_college, '学院管理')
        school_admin_id = ensure_user('test_school_admin', 'school_approver', '【测试】学校管理员', '信息化建设管理处', '校级管理')

        cc_college_leader_id = ensure_user('test_cc_college_leader', 'judge', '【测试】院赛评审组长', cs_college, '评委')
        cc_college_j1_id = ensure_user('test_cc_college_judge1', 'judge', '【测试】院赛评委1', cs_college, '评委')
        cc_college_j2_id = ensure_user('test_cc_college_judge2', 'judge', '【测试】院赛评委2', cs_college, '评委')

        cc_school_social_leader_id = ensure_user('test_cc_school_social_leader', 'judge', '【测试】校赛社科组长', None, '评委')
        cc_school_social_j1_id = ensure_user('test_cc_school_social_judge1', 'judge', '【测试】校赛社科评委1', None, '评委')
        cc_school_social_j2_id = ensure_user('test_cc_school_social_judge2', 'judge', '【测试】校赛社科评委2', None, '评委')

        cc_school_science_leader_id = ensure_user('test_cc_school_science_leader', 'judge', '【测试】校赛理工组长', None, '评委')
        cc_school_science_j1_id = ensure_user('test_cc_school_science_judge1', 'judge', '【测试】校赛理工评委1', None, '评委')
        cc_school_science_j2_id = ensure_user('test_cc_school_science_judge2', 'judge', '【测试】校赛理工评委2', None, '评委')

        def ensure_team(name, level, college=None, discipline_group=None, leader_user_id=None):
            row = conn.execute('SELECT id FROM review_teams WHERE name = ? AND level = ?', (name, level)).fetchone()
            if row:
                conn.execute(
                    'UPDATE review_teams SET college = COALESCE(college, ?), discipline_group = COALESCE(discipline_group, ?), leader_user_id = COALESCE(leader_user_id, ?), enabled = 1 WHERE id = ?',
                    (college, discipline_group, leader_user_id, row['id'])
                )
                return row['id']
            conn.execute(
                'INSERT INTO review_teams (name, level, college, discipline_group, leader_user_id, enabled) VALUES (?, ?, ?, ?, ?, 1)',
                (name, level, college, discipline_group, leader_user_id)
            )
            return conn.execute('SELECT id FROM review_teams WHERE name = ? AND level = ?', (name, level)).fetchone()['id']

        def ensure_member(team_id, user_id, role_in_team='member'):
            row = conn.execute('SELECT id FROM review_team_members WHERE team_id = ? AND user_id = ?', (team_id, user_id)).fetchone()
            if row:
                conn.execute('UPDATE review_team_members SET role_in_team = ? WHERE id = ?', (role_in_team, row['id']))
                return
            conn.execute('INSERT INTO review_team_members (team_id, user_id, role_in_team) VALUES (?, ?, ?)', (team_id, user_id, role_in_team))

        college_team_id = ensure_team('计算机学院评审测试组', 'college', cs_college, None, cc_college_leader_id)
        ensure_member(college_team_id, cc_college_leader_id, 'leader')
        ensure_member(college_team_id, cc_college_j1_id, 'member')
        ensure_member(college_team_id, cc_college_j2_id, 'member')

        school_team_social_id = ensure_team('校赛社科类测试组', 'school', None, '社科组', cc_school_social_leader_id)
        ensure_member(school_team_social_id, cc_school_social_leader_id, 'leader')
        ensure_member(school_team_social_id, cc_school_social_j1_id, 'member')
        ensure_member(school_team_social_id, cc_school_social_j2_id, 'member')

        school_team_science_id = ensure_team('校赛理工类测试组', 'school', None, '理工组', cc_school_science_leader_id)
        ensure_member(school_team_science_id, cc_school_science_leader_id, 'leader')
        ensure_member(school_team_science_id, cc_school_science_j1_id, 'member')
        ensure_member(school_team_science_id, cc_school_science_j2_id, 'member')

        conn.execute(
            "UPDATE users SET department = ? WHERE role IN (?, ?, ?) AND (department IS NULL OR department = '')",
            ('校级管理', 'system_admin', 'project_admin', 'school_approver')
        )
        conn.execute(
            "UPDATE users SET college = ? WHERE role = ? AND (college IS NULL OR college = '')",
            ('信息化建设管理处', 'system_admin')
        )

        conn.commit()
    finally:
        conn.close()
