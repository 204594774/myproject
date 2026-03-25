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
