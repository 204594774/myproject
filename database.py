import sqlite3
import os
from werkzeug.security import generate_password_hash

def get_db_connection():
    # Force absolute path to ensure consistency across different execution contexts
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')
    print(f"DEBUG: Connecting to DB at {db_path}")
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=NORMAL')
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('PRAGMA busy_timeout=5000')
    except Exception:
        pass
    return conn

def init_db():
    if os.path.exists('database.db'):
        os.remove('database.db')
    
    conn = get_db_connection()
    
    # 1. 用户表 (Users)
    # role: system_admin, project_admin, college_approver, school_approver, judge, teacher, student
    conn.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT,
            real_name TEXT,
            identity_number TEXT,  -- 身份(证)/学号/工号
            department TEXT,       -- 所在院系
            college TEXT,          -- 所在学院 (对于学院审批者，这是他们管理的学院)
            personal_info TEXT,
            role TEXT NOT NULL,
            status TEXT DEFAULT 'active'  -- active, pending, disabled
        )
    ''')

    # 2. 项目基本信息表 (Projects)
    # status: pending (待学院审批), college_approved (待学校审批), school_approved (待评审), rated (已评审/完成), rejected (已驳回)
    conn.execute('''
        CREATE TABLE projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            leader_name TEXT,       -- 项目负责人
            advisor_name TEXT,      -- 指导老师
            department TEXT,        -- 所属院系
            college TEXT,           -- 所属学院
            project_type TEXT,      -- 项目类型
            level TEXT,             -- 项目级别
            status TEXT DEFAULT 'pending', 
            year TEXT,              -- 参赛年份
            
            abstract TEXT,          -- 摘要 (New)
            assessment_indicators TEXT, -- 考核指标 (New)

            created_by INTEGER NOT NULL, -- 关联用户ID
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            -- 审核反馈
            college_feedback TEXT,
            school_feedback TEXT,
            
            competition_id INTEGER, -- 关联的赛事ID (New)
            extra_info TEXT,        -- 额外信息 JSON (New)
            
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    ''')

    # 3. 项目成员信息表 (ProjectMembers)
    conn.execute('''
        CREATE TABLE project_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            is_leader BOOLEAN DEFAULT 0,
            name TEXT,
            student_id TEXT,
            college TEXT,
            major TEXT,
            contact TEXT,
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
        )
    ''')

    # 4. 创新项目信息表 (InnovationProjects)
    conn.execute('''
        CREATE TABLE innovation_projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER UNIQUE NOT NULL,
            project_source TEXT,
            background TEXT,
            content TEXT,
            innovation_point TEXT,
            schedule TEXT,
            budget TEXT,
            expected_result TEXT,
            risk_control TEXT,  -- 风险控制 (New)
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
        )
    ''')

    # 5. 创业项目信息表 (EntrepreneurshipProjects)
    conn.execute('''
        CREATE TABLE entrepreneurship_projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER UNIQUE NOT NULL,
            project_source TEXT,
            tech_maturity TEXT,
            enterprise_mentor TEXT,
            team_intro TEXT,
            financial_budget TEXT,
            risk_budget TEXT,
            product_manufacturing TEXT,
            innovation_content TEXT,
            market_prospect TEXT,
            investment_budget TEXT,
            operation_mode TEXT,
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
        )
    ''')
    
    # 6. 项目评审表 (ProjectReviews) - 新增
    conn.execute('''
        CREATE TABLE project_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            judge_id INTEGER NOT NULL,
            score INTEGER,
            comment TEXT,
            criteria_scores TEXT, -- JSON: {innovation: 90, feasibility: 85, ...}
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
            FOREIGN KEY (judge_id) REFERENCES users (id)
        )
    ''')

    # 11. 评审任务表 (ReviewTasks) - New
    conn.execute('''
        CREATE TABLE review_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            judge_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending', -- pending, completed
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
            FOREIGN KEY (judge_id) REFERENCES users (id)
        )
    ''')

    # 12. 系统日志表 (SystemLogs) - New
    conn.execute('''
        CREATE TABLE system_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT, -- LOGIN, AUDIT, REVIEW, etc.
            details TEXT,
            ip_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # 13. 系统设置表 (SystemSettings) - New
    conn.execute('''
        CREATE TABLE system_settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            description TEXT
        )
    ''')

    # 7. 消息通知表 (Notifications) - 新增
    conn.execute('''
        CREATE TABLE notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT,
            content TEXT,
            is_read BOOLEAN DEFAULT 0,
            type TEXT, -- system, project, approval
            meta TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # 8. 项目文件/报告表 (ProjectFiles) - 新增 (支持中期检查和结题)
    conn.execute('''
        CREATE TABLE project_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            file_type TEXT NOT NULL, -- application, midterm, conclusion
            file_path TEXT NOT NULL,
            original_filename TEXT,
            status TEXT DEFAULT 'pending', -- pending, approved, rejected
            feedback TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
        )
    ''')

    # 9. 公告/新闻表 (Announcements) - New
    conn.execute('''
        CREATE TABLE announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            type TEXT DEFAULT 'news', -- news, notice
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    ''')

    # 10. 赛事信息表 (Competitions) - New
    conn.execute('''
        CREATE TABLE competitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            level TEXT,             -- School, Provincial, National
            organizer TEXT,
            registration_start DATE,
            registration_end DATE,
            description TEXT,
            status TEXT DEFAULT 'active', -- active, upcoming, ended
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # --- 初始化预设数据 ---
    
    users = [
        # 系统管理员
        ('admin', 'admin123', 'system_admin', '系统管理员', '', '', ''),
        # 项目管理员
        ('proj_admin', 'admin123', 'project_admin', '教务处老师', '', '教务处', ''),
        # 学院审批者
        ('col_approver', 'admin123', 'college_approver', '学院书记', '信息学院', '行政', '信息学院'),
        # 学校审批者
        ('sch_approver', 'admin123', 'school_approver', '校领导', '', '行政', ''),
        # 评委老师
        ('judge1', 'admin123', 'judge', '王教授', '计算机学院（人工智能学院）', '计算机系', '信息学院'),
        # 指导老师
        ('teacher1', 'teacher123', 'teacher', '张老师', '信息学院', '计算机系', '信息学院'),
        # 学生
        ('student1', 'student123', 'student', '李同学', '信息学院', '软件工程', '信息学院')
    ]

    for u in users:
        conn.execute('''
            INSERT INTO users (username, password, role, real_name, college, department, identity_number) 
            VALUES (?, ?, ?, ?, ?, ?, '000000')
        ''', (u[0], generate_password_hash(u[1]), u[2], u[3], u[4], u[5]))

    conn.commit()
    conn.close()
    print("Database initialized with updated schema and roles.")

if __name__ == '__main__':
    init_db()
