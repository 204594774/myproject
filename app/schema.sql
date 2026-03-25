-- 高校项目管理系统 数据库结构

-- 1. 用户表
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    real_name TEXT,
    identity_number TEXT,
    department TEXT,
    college TEXT,
    personal_info TEXT,
    teaching_office TEXT,
    research_area TEXT,
    role TEXT NOT NULL,
    status TEXT DEFAULT 'active'
);

-- 2. 项目基本信息表
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    leader_name TEXT,
    advisor_name TEXT,
    department TEXT,
    college TEXT,
    project_type TEXT,
    template_type TEXT DEFAULT 'default',
    level TEXT,
    status TEXT DEFAULT 'pending', 
    year TEXT,
    abstract TEXT,
    assessment_indicators TEXT,
    created_by INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    college_feedback TEXT,
    school_feedback TEXT,
    competition_id INTEGER,
    extra_info TEXT,
    inspiration_source TEXT,
    linked_project_id INTEGER,
    review_stage TEXT,
    college_review_result TEXT,
    school_review_result TEXT,
    provincial_award_level TEXT,
    national_award_level TEXT,
    research_admin_opinion TEXT,
    department_head_opinion TEXT,
    FOREIGN KEY (created_by) REFERENCES users (id)
);

-- 2.1 项目升级申请表
CREATE TABLE IF NOT EXISTS project_upgrade_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    applicant_id INTEGER NOT NULL,
    from_level TEXT,
    to_level TEXT,
    status TEXT DEFAULT 'pending', -- pending/approved/rejected
    reason TEXT,
    reviewer_id INTEGER,
    review_comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    FOREIGN KEY (applicant_id) REFERENCES users (id),
    FOREIGN KEY (reviewer_id) REFERENCES users (id)
);

-- 2.2 项目获奖记录表
CREATE TABLE IF NOT EXISTS project_awards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    stage TEXT NOT NULL, -- provincial/national
    award_level TEXT NOT NULL, -- special/first/second/third/excellent/none
    award_name TEXT,
    award_time TEXT,
    issuer TEXT,
    created_by INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users (id)
);

-- 3. 项目成员信息表
CREATE TABLE IF NOT EXISTS project_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    is_leader BOOLEAN DEFAULT 0,
    name TEXT,
    student_id TEXT,
    college TEXT,
    major TEXT,
    contact TEXT,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
);

-- 4. 创新项目信息表
CREATE TABLE IF NOT EXISTS innovation_projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER UNIQUE NOT NULL,
    project_source TEXT,
    background TEXT,
    content TEXT,
    innovation_point TEXT,
    schedule TEXT,
    budget TEXT,
    expected_result TEXT,
    risk_control TEXT,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
);

-- 5. 创业项目信息表
CREATE TABLE IF NOT EXISTS entrepreneurship_projects (
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
);

-- 6. 项目评审表
CREATE TABLE IF NOT EXISTS project_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    judge_id INTEGER NOT NULL,
    score INTEGER,
    comment TEXT,
    criteria_scores TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    FOREIGN KEY (judge_id) REFERENCES users (id)
);

-- 7. 评审任务表
CREATE TABLE IF NOT EXISTS review_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    judge_id INTEGER NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    FOREIGN KEY (judge_id) REFERENCES users (id)
);

-- 8. 系统日志表
CREATE TABLE IF NOT EXISTS system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT,
    details TEXT,
    ip_address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- 9. 系统设置表
CREATE TABLE IF NOT EXISTS system_settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    description TEXT
);

-- 10. 消息通知表
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT,
    content TEXT,
    is_read BOOLEAN DEFAULT 0,
    type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- 11. 项目文件表
CREATE TABLE IF NOT EXISTS project_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    file_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    original_filename TEXT,
    status TEXT DEFAULT 'pending',
    feedback TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
);

-- 12. 公告表
CREATE TABLE IF NOT EXISTS announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    type TEXT DEFAULT 'news',
    FOREIGN KEY (created_by) REFERENCES users (id)
);

-- 13. 赛事信息表
CREATE TABLE IF NOT EXISTS competitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    level TEXT,
    system_type TEXT,
    competition_level TEXT,
    national_organizer TEXT,
    school_organizer TEXT,
    organizer TEXT,
    registration_start DATE,
    registration_end DATE,
    description TEXT,
    status TEXT DEFAULT 'active',
    template_type TEXT DEFAULT 'default',
    form_config TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
