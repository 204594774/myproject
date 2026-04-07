import sqlite3
from flask import g
from config import get_config
import os
from werkzeug.security import generate_password_hash
from datetime import datetime

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
        if 'grade' not in cols:
            conn.execute('ALTER TABLE users ADD COLUMN grade TEXT')
        if 'enrollment_year' not in cols:
            conn.execute('ALTER TABLE users ADD COLUMN enrollment_year TEXT')
        if 'college_code' not in cols:
            conn.execute('ALTER TABLE users ADD COLUMN college_code TEXT')
        if 'major_code' not in cols:
            conn.execute('ALTER TABLE users ADD COLUMN major_code TEXT')
        if 'status' not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'active'")
        if 'roles' not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN roles TEXT")

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
        if 'college_award' not in project_cols:
            conn.execute("ALTER TABLE projects ADD COLUMN college_award TEXT DEFAULT 'none'")
        if 'school_award' not in project_cols:
            conn.execute("ALTER TABLE projects ADD COLUMN school_award TEXT DEFAULT 'none'")
        if 'research_admin_opinion' not in project_cols:
            conn.execute('ALTER TABLE projects ADD COLUMN research_admin_opinion TEXT')
        if 'department_head_opinion' not in project_cols:
            conn.execute('ALTER TABLE projects ADD COLUMN department_head_opinion TEXT')
        if 'is_recommended' not in project_cols:
            conn.execute('ALTER TABLE projects ADD COLUMN is_recommended INTEGER DEFAULT 0')
        if 'advisor_review_opinion' not in project_cols:
            conn.execute('ALTER TABLE projects ADD COLUMN advisor_review_opinion TEXT')
        if 'advisor_review_time' not in project_cols:
            conn.execute('ALTER TABLE projects ADD COLUMN advisor_review_time TIMESTAMP')
        if 'college_avg_score' not in project_cols:
            conn.execute('ALTER TABLE projects ADD COLUMN college_avg_score FLOAT')
        if 'school_avg_score' not in project_cols:
            conn.execute('ALTER TABLE projects ADD COLUMN school_avg_score FLOAT')
        if 'college_defense_score' not in project_cols:
            conn.execute('ALTER TABLE projects ADD COLUMN college_defense_score REAL')
        if 'college_recommend_rank' not in project_cols:
            conn.execute('ALTER TABLE projects ADD COLUMN college_recommend_rank INTEGER')
        if 'is_key_support' not in project_cols:
            conn.execute('ALTER TABLE projects ADD COLUMN is_key_support INTEGER DEFAULT 0')

        member_cols = [r[1] for r in conn.execute('PRAGMA table_info(project_members)').fetchall()]
        if 'grade' not in member_cols:
            conn.execute('ALTER TABLE project_members ADD COLUMN grade TEXT')
        if 'role' not in member_cols:
            conn.execute('ALTER TABLE project_members ADD COLUMN role TEXT')

        notif_cols = [r[1] for r in conn.execute('PRAGMA table_info(notifications)').fetchall()]
        if 'meta' not in notif_cols:
            conn.execute('ALTER TABLE notifications ADD COLUMN meta TEXT')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS reviewer_conflicts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reviewer_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                conflict_type TEXT,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (reviewer_id) REFERENCES users (id),
                FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
            )
        ''')

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
                recommend_national INTEGER DEFAULT 0,
                created_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        ''')

        award_cols = [r[1] for r in conn.execute('PRAGMA table_info(project_awards)').fetchall()]
        if 'recommend_national' not in award_cols:
            conn.execute('ALTER TABLE project_awards ADD COLUMN recommend_national INTEGER DEFAULT 0')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS post_event_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL UNIQUE,
                submitted_by INTEGER NOT NULL,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending',
                reject_reason TEXT,
                reviewed_by INTEGER,
                reviewed_at TIMESTAMP,
                provincial_award_level TEXT,
                provincial_certificate_no TEXT,
                provincial_certificate_file TEXT,
                provincial_advance_national INTEGER DEFAULT 0,
                national_award_level TEXT,
                national_certificate_no TEXT,
                national_certificate_file TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
                FOREIGN KEY (submitted_by) REFERENCES users (id),
                FOREIGN KEY (reviewed_by) REFERENCES users (id)
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
            ('国创赛', '["校赛","省赛","国赛"]', 0, 0),
            ('小挑', '["校赛","省赛","国赛"]', 0, 0),
            ('三创赛常规赛', '["校赛","省赛","国赛"]', 0, 0),
            ('三创赛实战赛', '["校赛","省赛","国赛"]', 0, 0),
            ('大创创新训练', '["学生申报","导师审核","学院资格审核","学院评审答辩","学院排序","学校复审","立项","中期检查","结题验收"]', 1, 1),
            ('大创创业训练', '["学生申报","双导师审核","学校统一评审","学校复审","立项","中期检查","结题验收"]', 1, 1),
            ('大创创业实践', '["学生申报","双导师审核","学校统一评审","学校复审","立项","中期检查","结题验收"]', 1, 1),
            ('大学生创新创业训练计划', '["学生申报","导师审核","学院资格审核","学院评审答辩","学院排序","学校复审","立项","中期检查","结题验收"]', 1, 1)
        ''')

        # 独立配置每个模板的获奖等级
        conn.execute('DELETE FROM award_levels')
        conn.execute('''
            INSERT INTO award_levels (template_id, level_options)
            SELECT id, '["特等奖","一等奖","二等奖","三等奖"]' FROM process_templates WHERE template_name IN ('大挑', '国创赛', '小挑', '三创赛常规赛', '三创赛实战赛')
        ''')
        conn.execute('''
            INSERT INTO award_levels (template_id, level_options)
            SELECT id, '["优秀","良好","合格","不合格"]' FROM process_templates WHERE template_name IN ('大创创新训练', '大创创业训练', '大创创业实践')
        ''')
        conn.execute('''
            INSERT INTO award_levels (template_id, level_options)
            SELECT id, '["优秀","良好","合格","不合格"]' FROM process_templates WHERE template_name IN ('大学生创新创业训练计划')
        ''')

        # 配置流程节点状态
        conn.execute('DELETE FROM process_node_status')
        # 大挑专属节点
        for node in ["学院赛", "校赛", "省赛", "国赛"]:
            status = '["待评审","已推荐","未推荐"]' if node in ["学院赛", "校赛"] else ('["待评审","已晋级","未晋级"]' if node == "省赛" else '["待评审","已获奖","未获奖"]')
            conn.execute('''
                INSERT INTO process_node_status (template_id, node_name, status_options)
                SELECT id, ?, ? FROM process_templates WHERE template_name = '大挑'
            ''', (node, status))
        
        # 国创赛, 小挑, 三创赛节点 (校赛 → 省赛 → 国赛)
        for template in ['国创赛', '小挑', '三创赛常规赛', '三创赛实战赛']:
            for node in ["校赛", "省赛", "国赛"]:
                status = '["待评审","已推荐","未推荐"]' if node == "校赛" else ('["待评审","已晋级","未晋级"]' if node == "省赛" else '["待评审","已获奖","未获奖"]')
                conn.execute('''
                    INSERT INTO process_node_status (template_id, node_name, status_options)
                    SELECT id, ?, ? FROM process_templates WHERE template_name = ?
                ''', (node, status, template))

        nodes_innovation_training = [
            ("学生申报", '["已提交","退回修改"]'),
            ("导师审核", '["待审核","通过","驳回"]'),
            ("学院资格审核", '["待审核","通过","驳回"]'),
            ("学院评审答辩", '["待答辩","已评分"]'),
            ("学院排序", '["待排序","已推荐","未推荐"]'),
            ("学校复审", '["待复审","通过","驳回"]'),
            ("立项", '["待立项","已立项","驳回"]'),
            ("中期检查", '["待提交","待审核","通过","需整改","不通过"]'),
            ("结题验收", '["待提交","待审核","通过","不通过"]')
        ]
        for node, status in nodes_innovation_training:
            conn.execute('''
                INSERT INTO process_node_status (template_id, node_name, status_options)
                SELECT id, ?, ? FROM process_templates WHERE template_name = ?
            ''', (node, status, '大创创新训练'))
            conn.execute('''
                INSERT OR IGNORE INTO process_node_status (template_id, node_name, status_options)
                SELECT id, ?, ? FROM process_templates WHERE template_name = ?
            ''', (node, status, '大学生创新创业训练计划'))

        nodes_entrepreneurship = [
            ("学生申报", '["已提交","退回修改"]'),
            ("双导师审核", '["待审核","通过","驳回"]'),
            ("学校统一评审", '["待评审","已评审"]'),
            ("学校复审", '["待复审","通过","驳回"]'),
            ("立项", '["待立项","已立项","驳回"]'),
            ("中期检查", '["待提交","待审核","通过","需整改","不通过"]'),
            ("结题验收", '["待提交","待审核","通过","不通过"]')
        ]
        for template in ['大创创业训练', '大创创业实践']:
            for node, status in nodes_entrepreneurship:
                conn.execute('''
                    INSERT INTO process_node_status (template_id, node_name, status_options)
                    SELECT id, ?, ? FROM process_templates WHERE template_name = ?
                ''', (node, status, template))

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
        try:
            conn.execute('ALTER TABLE review_tasks ADD COLUMN is_conflict INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute('ALTER TABLE review_tasks ADD COLUMN conflict_reason TEXT')
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute('ALTER TABLE review_tasks ADD COLUMN is_temporary INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute('ALTER TABLE review_tasks ADD COLUMN declaration INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute('ALTER TABLE review_tasks ADD COLUMN score_details TEXT')
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute('ALTER TABLE review_tasks ADD COLUMN is_recommended INTEGER DEFAULT 0')
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

        # 经验库表（项目往届经验库）
        # 兼容旧版本：旧库可能只有 methodology_summary/expert_comments/ppt_url/borrowed_count
        conn.execute('''
            CREATE TABLE IF NOT EXISTS project_legacy (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_project_id INTEGER,
                project_category TEXT,
                project_type TEXT,
                award_level TEXT,
                title TEXT NOT NULL,
                project_summary TEXT,
                methodology_summary TEXT,
                expert_comments TEXT,
                industry_field TEXT,
                team_experience TEXT,
                pitfalls TEXT,
                business_model_overview TEXT,
                ppt_url TEXT,
                borrowed_count INTEGER DEFAULT 0,
                is_public INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                submitted_by INTEGER,
                reviewed_by INTEGER,
                reviewed_at TIMESTAMP,
                reject_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        try:
            cols = [r[1] for r in conn.execute('PRAGMA table_info(project_legacy)').fetchall()]
            def ensure_add(col_name, alter_sql):
                if col_name not in cols:
                    conn.execute(alter_sql)

            ensure_add('project_category', "ALTER TABLE project_legacy ADD COLUMN project_category TEXT")
            ensure_add('project_type', "ALTER TABLE project_legacy ADD COLUMN project_type TEXT")
            ensure_add('award_level', "ALTER TABLE project_legacy ADD COLUMN award_level TEXT")
            ensure_add('project_summary', "ALTER TABLE project_legacy ADD COLUMN project_summary TEXT")
            ensure_add('industry_field', "ALTER TABLE project_legacy ADD COLUMN industry_field TEXT")
            ensure_add('team_experience', "ALTER TABLE project_legacy ADD COLUMN team_experience TEXT")
            ensure_add('pitfalls', "ALTER TABLE project_legacy ADD COLUMN pitfalls TEXT")
            ensure_add('business_model_overview', "ALTER TABLE project_legacy ADD COLUMN business_model_overview TEXT")
            ensure_add('ppt_url', "ALTER TABLE project_legacy ADD COLUMN ppt_url TEXT")
            ensure_add('borrowed_count', "ALTER TABLE project_legacy ADD COLUMN borrowed_count INTEGER DEFAULT 0")
            ensure_add('is_public', "ALTER TABLE project_legacy ADD COLUMN is_public INTEGER DEFAULT 0")
            ensure_add('status', "ALTER TABLE project_legacy ADD COLUMN status TEXT DEFAULT 'pending'")
            ensure_add('submitted_by', "ALTER TABLE project_legacy ADD COLUMN submitted_by INTEGER")
            ensure_add('reviewed_by', "ALTER TABLE project_legacy ADD COLUMN reviewed_by INTEGER")
            ensure_add('reviewed_at', "ALTER TABLE project_legacy ADD COLUMN reviewed_at TIMESTAMP")
            ensure_add('reject_reason', "ALTER TABLE project_legacy ADD COLUMN reject_reason TEXT")
            ensure_add('template_name', "ALTER TABLE project_legacy ADD COLUMN template_name TEXT")
            ensure_add('experience_sections', "ALTER TABLE project_legacy ADD COLUMN experience_sections TEXT")
        except Exception:
            # 即使 ALTER 失败，也不影响系统启动；接口按字段存在性工作
            pass

        # 借鉴记录表
        conn.execute('''
            CREATE TABLE IF NOT EXISTS project_borrow_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                legacy_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (legacy_id) REFERENCES project_legacy (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        try:
            cols = [r[1] for r in conn.execute('PRAGMA table_info(project_borrow_records)').fetchall()]
            if 'reason' not in cols:
                conn.execute('ALTER TABLE project_borrow_records ADD COLUMN reason TEXT')
        except Exception:
            pass

        conn.execute('''
            CREATE TABLE IF NOT EXISTS legacy_borrow_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                legacy_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                reason TEXT,
                status TEXT DEFAULT 'pending_teacher',
                reviewed_by INTEGER,
                reviewed_at TIMESTAMP,
                review_comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (legacy_id) REFERENCES project_legacy (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (reviewed_by) REFERENCES users (id)
            )
        ''')
        try:
            cols = [r[1] for r in conn.execute('PRAGMA table_info(legacy_borrow_requests)').fetchall()]
            def ensure_add_borrow_req(col_name, alter_sql):
                if col_name not in cols:
                    conn.execute(alter_sql)
            ensure_add_borrow_req('reason', "ALTER TABLE legacy_borrow_requests ADD COLUMN reason TEXT")
            ensure_add_borrow_req('status', "ALTER TABLE legacy_borrow_requests ADD COLUMN status TEXT DEFAULT 'pending_teacher'")
            ensure_add_borrow_req('reviewed_by', "ALTER TABLE legacy_borrow_requests ADD COLUMN reviewed_by INTEGER")
            ensure_add_borrow_req('reviewed_at', "ALTER TABLE legacy_borrow_requests ADD COLUMN reviewed_at TIMESTAMP")
            ensure_add_borrow_req('review_comment', "ALTER TABLE legacy_borrow_requests ADD COLUMN review_comment TEXT")
        except Exception:
            pass

        conn.execute('''
            CREATE TABLE IF NOT EXISTS legacy_pitfall_suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                legacy_id INTEGER NOT NULL,
                teacher_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                reviewed_by INTEGER,
                reviewed_at TIMESTAMP,
                review_comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (legacy_id) REFERENCES project_legacy (id) ON DELETE CASCADE,
                FOREIGN KEY (teacher_id) REFERENCES users (id)
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS legacy_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                legacy_id INTEGER NOT NULL,
                file_type TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                original_filename TEXT,
                uploaded_by INTEGER,
                status TEXT DEFAULT 'approved',
                reviewed_by INTEGER,
                reviewed_at TIMESTAMP,
                reject_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (legacy_id) REFERENCES project_legacy (id) ON DELETE CASCADE,
                FOREIGN KEY (uploaded_by) REFERENCES users (id)
            )
        ''')
        try:
            cols = [r[1] for r in conn.execute('PRAGMA table_info(legacy_files)').fetchall()]
            def ensure_add_legacy_file(col_name, alter_sql):
                if col_name not in cols:
                    conn.execute(alter_sql)
            ensure_add_legacy_file('status', "ALTER TABLE legacy_files ADD COLUMN status TEXT DEFAULT 'approved'")
            ensure_add_legacy_file('reviewed_by', "ALTER TABLE legacy_files ADD COLUMN reviewed_by INTEGER")
            ensure_add_legacy_file('reviewed_at', "ALTER TABLE legacy_files ADD COLUMN reviewed_at TIMESTAMP")
            ensure_add_legacy_file('reject_reason', "ALTER TABLE legacy_files ADD COLUMN reject_reason TEXT")
        except Exception:
            pass

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

        conn.execute('''
            CREATE TABLE IF NOT EXISTS review_promotion_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                competition_id INTEGER NOT NULL,
                review_level TEXT NOT NULL,
                scope_key TEXT DEFAULT '',
                rule_type TEXT NOT NULL,
                rule_value REAL NOT NULL,
                updated_by INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(competition_id, review_level, scope_key),
                FOREIGN KEY (competition_id) REFERENCES competitions(id) ON DELETE CASCADE,
                FOREIGN KEY (updated_by) REFERENCES users(id)
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
            conn.execute('ALTER TABLE projects ADD COLUMN provincial_certificate_file TEXT')
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
            conn.execute('ALTER TABLE projects ADD COLUMN national_certificate_file TEXT')
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute('ALTER TABLE projects ADD COLUMN national_review_comment TEXT')
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute('ALTER TABLE projects ADD COLUMN college_result_locked INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute('ALTER TABLE projects ADD COLUMN school_result_locked INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute('ALTER TABLE projects ADD COLUMN college_published_at TIMESTAMP')
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute('ALTER TABLE projects ADD COLUMN school_published_at TIMESTAMP')
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

        cs_college = '计算机学院（人工智能学院）'
        # 学院管理员：管理大创项目审核 + 大挑学院赛评审 (college_approver)
        college_admin_id = ensure_user('test_college_admin_cs', 'college_approver', '【测试】计算机学院管理员', cs_college, '学院管理')
        
        # 学校管理员：管理大创终审 + 大挑校赛/省赛/国赛结果录入 (school_approver)
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

        # 统一数据库中已有的学院名称
        conn.execute("UPDATE users SET college = ? WHERE college = '计算机学院'", (cs_college,))
        conn.execute("UPDATE projects SET college = ? WHERE college = '计算机学院'", (cs_college,))
        conn.execute("UPDATE review_teams SET college = ? WHERE college = '计算机学院'", (cs_college,))

        conn.execute(
            "UPDATE users SET department = ? WHERE role IN (?, ?, ?) AND (department IS NULL OR department = '')",
            ('校级管理', 'system_admin', 'project_admin', 'school_approver')
        )
        conn.execute(
            "UPDATE users SET college = ? WHERE role = ? AND (college IS NULL OR college = '')",
            ('信息化建设管理处', 'system_admin')
        )

        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS jiebang_topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER NOT NULL,
                group_no INTEGER NOT NULL,
                group_name TEXT NOT NULL,
                topic_no INTEGER NOT NULL,
                topic_title TEXT NOT NULL,
                topic_desc TEXT,
                enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
            )
            '''
        )
        conn.execute('CREATE INDEX IF NOT EXISTS idx_jiebang_topics_year_group ON jiebang_topics(year, group_no, topic_no)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_jiebang_topics_enabled ON jiebang_topics(year, enabled)')

        existing_2026 = conn.execute('SELECT COUNT(*) AS c FROM jiebang_topics WHERE year = 2026').fetchone()['c']
        if existing_2026 == 0:
            seed = [
                (2026, 1, '“新工科+优秀传统文化”融合项目群', 1, '土家织锦AI纹样生成平台', '用GAN算法学习传统纹样，一键生成新式样并适配数控织机。', 1),
                (2026, 1, '“新工科+优秀传统文化”融合项目群', 2, '苗族银饰3D打印与智能定制', '开发银饰参数化设计库，支持用户在线修改并直连3D打印工坊。', 1),
                (2026, 1, '“新工科+优秀传统文化”融合项目群', 3, '建筑数字化保护平台', '无人机扫描吊脚楼等建筑，生成三维模型用于修复与文化展示。', 1),
                (2026, 1, '“新工科+优秀传统文化”融合项目群', 4, '非遗乐器声学分析与智能调音器', '采集独弦琴、芦笙等音色数据，开发智能调音APP与数字乐器库。', 1),
                (2026, 1, '“新工科+优秀传统文化”融合项目群', 5, '壮族铜鼓纹样激光雕刻系统', '将铜鼓纹样转化为激光雕刻路径，应用于文创产品定制。', 1),
                (2026, 1, '“新工科+优秀传统文化”融合项目群', 6, '非遗服饰可穿戴智能织物', '在苗绣、土家织锦中嵌入柔性传感器，实现温控与健康数据监测。', 1),
                (2026, 1, '“新工科+优秀传统文化”融合项目群', 7, '非遗陶瓷釉料数字化配比系统', '基于机器学习优化釉料配方，复原与创新建水陶、藏陶等工艺。', 1),
                (2026, 1, '“新工科+优秀传统文化”融合项目群', 8, '边疆传统村落智慧能源管理系统', '针对木结构民居设计光伏瓦片+储能系统，实现低干扰能源改造。', 1),
                (2026, 2, '“人工智能+”应用项目群', 1, '病虫害AI识别小程序', '农民拍照识别作物病害，推送双语防治方案。', 1),
                (2026, 2, '“人工智能+”应用项目群', 2, '古籍智能校注平台', '用OCR+自然语言处理识别古籍文献，辅助学者标注与研究。', 1),
                (2026, 2, '“人工智能+”应用项目群', 3, '非遗歌舞动作AI教学系统', '摄像头捕捉用户动作，对比标准舞姿（如傣族舞）并生成纠正反馈。', 1),
                (2026, 2, '“人工智能+”应用项目群', 4, '区域情感语音合成系统', '合成带情感特征的语言语音，用于有声故事、虚拟导游。', 1),
                (2026, 2, '“人工智能+”应用项目群', 5, '特色食材智能推荐与食谱生成', '基于用户本地食材（如酥油、蕨菜）推荐健康菜谱与烹饪指导。', 1),
                (2026, 2, '“人工智能+”应用项目群', 6, '西部山区自然灾害AI预警平台', '结合地质与气象数据，为山区泥石流、滑坡提供多语言预警。', 1),
                (2026, 2, '“人工智能+”应用项目群', 7, '民族医药方剂智能配伍辅助系统', '输入症状与体质，推荐民族药方并提示禁忌与现代药理说明。', 1),
                (2026, 2, '“人工智能+”应用项目群', 8, '非遗手工艺人直播智能助手', '自动生成多语言字幕、实时翻译评论，提升跨境直播效果。', 1),
                (2026, 3, '低空经济边疆场景项目群', 1, '“天路使者”高山无人机血袋配送网络', '在川滇高山地区建立无人机血站直达乡镇卫生院的常态化配送体系。', 1),
                (2026, 3, '低空经济边疆场景项目群', 2, '边境珍稀植物无人机巡护系统', '用无人机+多光谱监测跨境区域珍稀植物，防范盗采与生态变化。', 1),
                (2026, 3, '低空经济边疆场景项目群', 3, '高原松茸无人机快速采集与冷链运输', '设计轻量采摘装置，实现高海拔松茸当日下山直达机场。', 1),
                (2026, 3, '低空经济边疆场景项目群', 4, '特色非遗节庆无人机全景直播服务平台', '为三月三、那达慕、火把节、泼水节等提供定制化航拍直播与短视频生成服务。', 1),
                (2026, 3, '低空经济边疆场景项目群', 5, '跨境无人机快递“数字边贸通道”', '在中缅边境试点无人机跨境小件快递，配套数字化清关系统。', 1),
                (2026, 3, '低空经济边疆场景项目群', 6, '特色村寨火灾无人机预警与灭火弹投放系统', '红外监测与灭火弹精准投放，应对木质建筑火灾。', 1),
                (2026, 3, '低空经济边疆场景项目群', 7, '草原鼠害无人机监测与精准投药', '识别鼠洞分布，控制投药量以减少生态破坏。', 1),
                (2026, 3, '低空经济边疆场景项目群', 8, '雪山冰川无人机动态监测网络', '监测冰川消融，为高原水资源管理提供数据。', 1),
                (2026, 3, '低空经济边疆场景项目群', 9, '山区校车无人机伴随护航系统', '无人机实时监控险峻路段，预警落石并提供通信中继。', 1),
                (2026, 4, '生物技术+资源项目群', 1, '傣药“辣木”降血糖成分定向提取与制剂开发', '利用酶工程技术提高活性成分提取率，开发辅助降糖产品。', 1),
                (2026, 4, '生物技术+资源项目群', 2, '雪域高原特有酵母菌种库与高原发酵食品开发', '分离青稞酒、酸奶中独特菌种，研发高原特色益生菌产品。', 1),
                (2026, 4, '生物技术+资源项目群', 3, '特色昆虫蛋白资源化利用', '将竹虫、蜂蛹等传统食用昆虫开发为高蛋白营养粉与宠物饲料。', 1),
                (2026, 4, '生物技术+资源项目群', 4, '抗高原缺氧藏药组方分子机制解析与改良', '用代谢组学分析“红景天”等复方，开发抗疲劳功能性食品。', 1),
                (2026, 4, '生物技术+资源项目群', 5, '植物天然染料微生物发酵制备', '用工程菌发酵生产苏木、蓝靛等染料，替代化学合成工艺。', 1),
                (2026, 4, '生物技术+资源项目群', 6, '一带一路遗传资源数字化保护与伦理数据库', '建立一带一路特有作物、家畜遗传资源数据库，制定惠益分享准则。', 1),
                (2026, 4, '生物技术+资源项目群', 7, '发酵马奶益生菌口腔护理产品', '分离马奶中独特乳酸菌，开发抗龋齿牙膏或漱口水。', 1),
                (2026, 4, '生物技术+资源项目群', 8, '特色食用菌深层发酵功能成分生产', '利用发酵罐量产松茸多糖、牛肝菌多肽等高端原料。', 1),
                (2026, 4, '生物技术+资源项目群', 9, '基于苗医“滚蛋疗法”的透皮给药载体开发', '研发仿生蛋膜微针贴片，实现苗药成分的缓释透皮吸收。', 1),
                (2026, 4, '生物技术+资源项目群', 10, '边疆地区污水微生物燃料电池+生态修复系统', '利用本地微生物构建低成本污水处理与产能一体化装置。', 1),
                (2026, 5, '量子科技前沿探索项目群', 1, '道地药材有效成分量子计算模拟平台', '与超算中心合作，模拟药物分子与靶点结合过程，加速藏药、苗药筛选。', 1),
                (2026, 5, '量子科技前沿探索项目群', 2, '青藏高原气候变化量子机器学习预测模型', '用量子算法优化青藏高原气候预测模型，服务生态保护。', 1),
                (2026, 5, '量子科技前沿探索项目群', 3, '特色合金材料量子尺度设计', '模拟藏银、苗银等微观结构，设计高性能抗氧化合金配方。', 1),
                (2026, 5, '量子科技前沿探索项目群', 4, '基于量子随机数的非遗艺术NFT加密与确权系统', '为非遗数字艺术品提供量子级加密的版权保护与追溯。', 1),
                (2026, 5, '量子科技前沿探索项目群', 5, '“中巴经济走廊”物流路径量子优化系统', '针对复杂地形物流，用量子算法规划最优路径。', 1),
                (2026, 5, '量子科技前沿探索项目群', 6, '量子传感支持的高原地震早期预警网络', '研发高灵敏度量子重力仪，监测青藏高原板块微动。', 1),
                (2026, 5, '量子科技前沿探索项目群', 7, '传统图案量子神经网络生成艺术研究', '用量子启发算法生成前所未有的特色风格几何图案。', 1),
                (2026, 5, '量子科技前沿探索项目群', 8, '量子计算辅助的《格萨尔王》信息熵分析', '量化《格萨尔王》等史诗的信息复杂度与传播变异规律。', 1),
                (2026, 5, '量子科技前沿探索项目群', 9, '面向量子时代的科技伦理教育课程开发', '编写量子计算、基因编辑等技术的科技伦理教材。', 1),
                (2026, 6, '新能源+边疆可持续发展项目群', 1, '高原移动式光伏储能充电桩网络', '为牧民转场、自驾旅游提供模块化、可搬运的光储充一体化设备。', 1),
                (2026, 6, '新能源+边疆可持续发展项目群', 2, '藏式民居“阳光间”智能采暖系统', '结合传统阳光房设计，用相变储热材料与智能调控实现零耗电采暖。', 1),
                (2026, 6, '新能源+边疆可持续发展项目群', 3, '边境哨所/海岛风光氢储互补微电网', '为无市电哨所设计风电+光伏+电解制氢+燃料电池的可靠能源系统。', 1),
                (2026, 6, '新能源+边疆可持续发展项目群', 4, '山区村寨小水电增效增功智能控制系统', '对老旧小水电进行数字化改造，实现发电预测与电网友好并网。', 1),
                (2026, 6, '新能源+边疆可持续发展项目群', 5, '南方木结构民居防潮光伏通风一体化', '研发兼具发电、防潮、通风功能的仿传统外观光伏瓦。', 1),
                (2026, 6, '新能源+边疆可持续发展项目群', 6, '高原畜牧业粪污沼气发电与碳交易项目开发', '建设村级沼气电站，并开发CCER方法学实现碳汇增收。', 1),
                (2026, 6, '新能源+边疆可持续发展项目群', 7, '边疆口岸“光伏+跨境贸易”绿色能源合作社', '在口岸建设光伏棚，为贸易市场供电，收益共享。', 1),
                (2026, 6, '新能源+边疆可持续发展项目群', 8, '新能源汽车退役电池梯次利用储能系统', '回收城市退役电池，用于基站、路灯等分布式储能。', 1),
                (2026, 6, '新能源+边疆可持续发展项目群', 9, '“能源民俗学”数字博物馆与节能教育平台', '数字化展示传统能源智慧，推广现代节能技术。', 1),
                (2026, 7, '新材料+优秀传统工艺创新项目群', 1, '古法造纸纳米增强与防蛀耐久性改进', '用纳米纤维素加固传统古法造纸，延长古籍修复与艺术品寿命。', 1),
                (2026, 7, '新材料+优秀传统工艺创新项目群', 2, '苗绣导电绣线开发与智能刺绣服装', '研发可刺绣的柔性导电绣线，实现服装触摸交互与健康监测。', 1),
                (2026, 7, '新材料+优秀传统工艺创新项目群', 3, '建筑涂料的光催化自清洁功能化', '基于石灰、黄土等传统材料，添加光催化剂实现墙面自清洁。', 1),
                (2026, 7, '新材料+优秀传统工艺创新项目群', 4, '蒙古包用蓄热相变材料与轻质保温复合材料', '改进毛毡保温层，实现日间蓄热、夜间放热的智能温控。', 1),
                (2026, 7, '新材料+优秀传统工艺创新项目群', 5, '天然植物染料敏化太阳能电池', '用苏木、黄檗等染料研制彩色、半透明柔性太阳能电池，用于建筑一体化。', 1),
                (2026, 7, '新材料+优秀传统工艺创新项目群', 6, '漆器生物基可降解涂层开发', '用植物树脂替代部分化学漆，开发环保型民族漆器。', 1),
                (2026, 7, '新材料+优秀传统工艺创新项目群', 7, '纺织废料再生环保建材', '将废旧纺织品破碎，与粘合材料复合制成隔音板、装饰板。', 1),
                (2026, 7, '新材料+优秀传统工艺创新项目群', 8, '抗紫外线户外运动面料', '结合扎染、蜡染图案，开发兼具传统美学与高性能的户外服装面料。', 1),
                (2026, 7, '新材料+优秀传统工艺创新项目群', 9, '智能调光特色玻璃', '将stained glass工艺与电致变色技术结合，用于特色建筑与高端酒店。', 1),
                (2026, 8, '脑机接口+医学探索项目群', 1, '结合“情志理论”的情绪调节神经反馈游戏', '开发针对焦虑、抑郁的脑电生物反馈游戏，融入传统医学理念。', 1),
                (2026, 8, '脑机接口+医学探索项目群', 2, '脑机接口康复训练系统', '为失语症患者设计视觉/听觉诱发电位的康复工具。', 1),
                (2026, 8, '脑机接口+医学探索项目群', 3, '多模态脑机接口音乐创作平台', '通过脑波与肌电信号控制音色、节奏，生成民族风格电子音乐。', 1),
                (2026, 8, '脑机接口+医学探索项目群', 4, '无创脑刺激缓解高原疲劳与睡眠障碍的可穿戴设备', '研发经颅电刺激头带，缓解高原反应相关症状。', 1),
                (2026, 8, '脑机接口+医学探索项目群', 5, '图案视觉诱发脑波分析与美学评价系统', '通过脑波客观分析不同人群对传统文化图案的审美反应。', 1),
                (2026, 8, '脑机接口+医学探索项目群', 6, '基于运动想象的传统舞蹈动作辅助学习系统', '通过想象舞蹈动作触发视觉反馈，辅助初学者学习复杂舞步。', 1),
                (2026, 8, '脑机接口+医学探索项目群', 7, '脑控智能假肢', '为残障人士开发可执行特定手势（如手印、礼仪动作）的假肢。', 1),
                (2026, 8, '脑机接口+医学探索项目群', 8, '结合中医经络的便携式经穴电刺激与脑波监测仪', '验证特定穴位刺激对脑波的影响，探索科学解释。', 1),
                (2026, 8, '脑机接口+医学探索项目群', 9, '学生课堂注意力脑波监测与改善方案', '无感监测学生注意力，结合游戏设计提升专注力的干预活动。', 1),
                (2026, 9, '人形机器人+社会服务项目群', 1, '博物馆讲解机器人', '具备特色形象特征，支持语音问答、舞蹈演示等。', 1),
                (2026, 9, '人形机器人+社会服务项目群', 2, '传统武术动作模仿与教学机器人', '可演示太极拳、少林拳、八段锦等动作，纠正学习者姿势。', 1),
                (2026, 9, '人形机器人+社会服务项目群', 3, '偏远村寨老年陪护机器人', '具备送药提醒、视频通话、跌倒监测功能，界面适配老人。', 1),
                (2026, 9, '人形机器人+社会服务项目群', 4, '传统乐器演奏机器人乐队', '开发可演奏编钟、马头琴、都塔尔等乐器的机器人，用于文化展演。', 1),
                (2026, 9, '人形机器人+社会服务项目群', 5, '非遗技艺演示机器人“绣娘助手”', '演示苏绣、土家织锦基本针法，辅助传承人教学。', 1),
                (2026, 9, '人形机器人+社会服务项目群', 6, '高原边境巡逻机器人', '适应高寒地形，具备人脸识别、异常情况报警功能。', 1),
                (2026, 9, '人形机器人+社会服务项目群', 7, '特色餐厅服务机器人', '可进行简单语言点餐、送餐，并介绍菜品文化背景。', 1),
                (2026, 9, '人形机器人+社会服务项目群', 8, '机器人传统体育竞赛', '设计摔跤、射箭、毽球等机器人，举办赛事激发青少年工程兴趣。', 1),
                (2026, 10, '新质生产力赋能平台项目群', 1, '“丝路物联”跨境贸易区块链溯源平台', '为藏毯、滇红茶等提供从原料到出口的全流程可追溯数字护照。', 1),
                (2026, 10, '新质生产力赋能平台项目群', 2, '边疆地区碳汇计量与交易服务平台', '用遥感与AI计量森林/草原碳汇，对接全国碳市场助农增收。', 1),
                (2026, 10, '新质生产力赋能平台项目群', 3, '手工艺人才远程协作与技能共享平台', '连接散居各地的手工艺人、艺术家，开展远程协同创作。', 1),
                (2026, 10, '新质生产力赋能平台项目群', 4, '边疆“低空物流+应急”综合调度云平台', '整合多家无人机物流与应急服务，实现统一调度与空域协商。', 1),
                (2026, 10, '新质生产力赋能平台项目群', 5, '特色成分高通量筛选与知识产权服务平台', '建立特色药用植物、微生物成分数据库，提供专利分析与转化服务。', 1),
                (2026, 10, '新质生产力赋能平台项目群', 6, '“数字孪生”传统村落管理与旅游平台', '构建村落数字孪生体，用于规划、灾害模拟、虚拟旅游。', 1),
                (2026, 10, '新质生产力赋能平台项目群', 7, '智能制造共享工厂网络', '在县域布局3D打印、数控裁剪等共享车间，服务小微企业。', 1),
                (2026, 10, '新质生产力赋能平台项目群', 8, '跨境文化大数据安全计算平台', '在保障文化数据安全前提下，支持国内外学者开展合作研究。', 1),
                (2026, 10, '新质生产力赋能平台项目群', 9, '青年科创“飞地孵化器”网络', '在北上广深、省会城市等设立孵化基地，支持“异地研发，本地转化”。', 1),
                (2026, 11, '新文科建设项目群', 1, '“纹韵解码”——基于AI的民族服饰纹样数字化与文创应用平台', '利用图像识别与生成式AI，系统化采集、解析民族服饰纹样文化符号，建立可商业化的“纹样基因库”。', 1),
                (2026, 11, '新文科建设项目群', 2, '“智慧山谣”——基于情感计算的民歌VR沉浸式教学系统', '通过VR场景还原民歌演唱环境，结合情感识别技术实时纠正演唱者的情绪表达。', 1),
                (2026, 11, '新文科建设项目群', 3, '“共栖之窗”——城市社区民族融合沉浸式影像档案馆', '采集多民族聚居社区口述史与生活影像，通过3D建模还原社区变迁，打造线上线下融合“社区记忆展”。', 1),
                (2026, 11, '新文科建设项目群', 4, '“古道新生”——南方丝绸之路数字研学平台', '整合丝绸之路历史资料，开发AR实景导航研学路线，与旅行社、高校合作推出研学营。', 1),
                (2026, 11, '新文科建设项目群', 5, '“节律感知”——多民族传统节庆文化体验箱', '设计包含节庆道具、AR卡片、音视频教程的实体体验箱，配套小程序支持知识问答与互动。', 1),
                (2026, 11, '新文科建设项目群', 6, '“植愈密码”——民族植物医药文化科普与芳香疗法产品开发', '挖掘民族药用植物智慧，结合现代芳疗技术开发产品，并与院校合作验证功效。', 1),
                (2026, 11, '新文科建设项目群', 7, '“田野之眼”——民族志研究者智能田野调查工具包', '集成多语言录音转写、访谈语义分析、民族志数据可视化功能，降低田野调查成本。', 1),
                (2026, 11, '新文科建设项目群', 8, '砖茶“数字万里茶道”——基于区块链的跨境文化遗产数字孪生平台', '构建区块链+数字孪生系统，沉浸式漫游与档案上链存证，并设计互动游戏增强参与。', 1),
                (2026, 11, '新文科建设项目群', 9, '“茶道复兴体”——万里茶道沿线文旅融合与社区赋能社会企业模式', '设计“茶道振兴工具箱”，成立社会企业运营，利润反哺非遗保护与社区教育。', 1),
                (2026, 11, '新文科建设项目群', 10, '“记忆典当行”——基于非遗技艺的老年人认知干预与价值再生计划', '探索“技艺回溯”工作坊、“记忆实物化”产品线与数字化“记忆地图”等方案。', 1),
                (2026, 11, '新文科建设项目群', 11, '“银发留学记”——老年人高校沉浸式生命教育项目与高校资源活化方案', '探索“高校体验卡”课程包、“青春存档”计划与“校园创生”伙伴制度等方案。', 1),
            ]
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            conn.executemany(
                'INSERT INTO jiebang_topics (year, group_no, group_name, topic_no, topic_title, topic_desc, enabled, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                [(y, gno, gname, tno, tt, td, en, now) for (y, gno, gname, tno, tt, td, en) in seed]
            )

        conn.execute('''
            CREATE TABLE IF NOT EXISTS auth_tokens (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                active_role TEXT NOT NULL,
                all_roles TEXT,
                college TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT,
                content TEXT,
                meta TEXT,
                is_read BOOLEAN DEFAULT 0,
                type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                type TEXT DEFAULT 'news',
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        ''')

        try:
            n_cols = [r[1] for r in conn.execute('PRAGMA table_info(notifications)').fetchall()]
            if 'title' not in n_cols:
                conn.execute('ALTER TABLE notifications ADD COLUMN title TEXT')
            if 'content' not in n_cols:
                conn.execute('ALTER TABLE notifications ADD COLUMN content TEXT')
            if 'meta' not in n_cols:
                conn.execute('ALTER TABLE notifications ADD COLUMN meta TEXT')
            if 'type' not in n_cols:
                conn.execute('ALTER TABLE notifications ADD COLUMN type TEXT')
            if 'is_read' not in n_cols:
                conn.execute('ALTER TABLE notifications ADD COLUMN is_read BOOLEAN DEFAULT 0')
            if 'created_at' not in n_cols:
                conn.execute('ALTER TABLE notifications ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        except Exception:
            pass

        conn.execute('CREATE INDEX IF NOT EXISTS idx_notifications_user_created ON notifications(user_id, created_at DESC)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_notifications_user_isread ON notifications(user_id, is_read)')

        try:
            hz = conn.execute("SELECT 1 FROM users WHERE username = ? LIMIT 1", ('黄卓',)).fetchone()
            if not hz:
                conn.execute(
                    '''
                    INSERT INTO users (username, password, role, real_name, identity_number, status, college, department)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''',
                    ('黄卓', generate_password_hash('hz123456'), config.ROLES['TEACHER'], '黄卓', '', 'active', '计算机学院（人工智能学院）', '')
                )
        except Exception:
            pass

        conn.commit()
    finally:
        conn.close()
