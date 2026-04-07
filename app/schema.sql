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
    college_award TEXT DEFAULT 'none',
    school_award TEXT DEFAULT 'none',
    provincial_award_level TEXT,
    national_award_level TEXT,
    provincial_status TEXT,
    provincial_certificate_no TEXT,
    provincial_certificate_file TEXT,
    provincial_advance_national INTEGER DEFAULT 0,
    provincial_review_comment TEXT,
    national_status TEXT,
    national_certificate_no TEXT,
    national_review_comment TEXT,
    national_certificate_file TEXT,
    research_admin_opinion TEXT,
    department_head_opinion TEXT,
    FOREIGN KEY (created_by) REFERENCES users (id)
);

-- 22. 赛后信息填报（获奖信息填报与审核）
CREATE TABLE IF NOT EXISTS post_event_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL UNIQUE,
    submitted_by INTEGER NOT NULL,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending', -- pending/approved/rejected
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
    recommend_national INTEGER DEFAULT 0,
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
    grade TEXT,
    role TEXT,
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
    score FLOAT DEFAULT 0,
    comments TEXT,
    score_details TEXT,
    is_temporary BOOLEAN DEFAULT 0,
    declaration BOOLEAN DEFAULT 0,
    is_recommended BOOLEAN DEFAULT 0,
    not_recommended_reasons TEXT,
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
    meta TEXT,
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

CREATE TABLE IF NOT EXISTS process_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_name TEXT NOT NULL UNIQUE,
    process_structure TEXT NOT NULL,
    has_mid_check BOOLEAN NOT NULL,
    has_final_acceptance BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS process_node_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id INTEGER NOT NULL,
    node_name TEXT NOT NULL,
    status_options TEXT NOT NULL,
    UNIQUE(template_id, node_name),
    FOREIGN KEY (template_id) REFERENCES process_templates(id)
);

CREATE TABLE IF NOT EXISTS award_levels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id INTEGER NOT NULL UNIQUE,
    level_options TEXT NOT NULL,
    FOREIGN KEY (template_id) REFERENCES process_templates(id)
);

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
);

INSERT OR IGNORE INTO process_templates (template_name, process_structure, has_mid_check, has_final_acceptance) VALUES
('大挑', '["学院赛","校赛","省赛","国赛"]', 0, 0),
('大创创新训练', '["学生申报","导师审核","学院资格审核","学院评审答辩","学院排序","学校复审","立项","中期检查","结题验收"]', 1, 1),
('国创赛', '["校赛","省赛","国赛"]', 0, 0),
('小挑', '["校赛","省赛","国赛"]', 0, 0),
('大创创业训练', '["学生申报","双导师审核","学校统一评审","学校复审","立项","中期检查","结题验收"]', 1, 1),
('大创创业实践', '["学生申报","双导师审核","学校统一评审","学校复审","立项","中期检查","结题验收"]', 1, 1),
('三创赛常规赛', '["校赛","省赛","国赛"]', 0, 0),
('三创赛实战赛', '["校赛","省赛","国赛"]', 0, 0);

INSERT OR IGNORE INTO process_node_status (template_id, node_name, status_options)
SELECT id, '学院赛', '["待评审","已推荐","未推荐"]' FROM process_templates WHERE template_name = '大挑';
INSERT OR IGNORE INTO process_node_status (template_id, node_name, status_options)
SELECT id, '校赛', '["待评审","已推荐","未推荐"]' FROM process_templates WHERE template_name = '大挑';
INSERT OR IGNORE INTO process_node_status (template_id, node_name, status_options)
SELECT id, '省赛', '["待评审","已晋级","未晋级"]' FROM process_templates WHERE template_name = '大挑';
INSERT OR IGNORE INTO process_node_status (template_id, node_name, status_options)
SELECT id, '国赛', '["待评审","已获奖","未获奖"]' FROM process_templates WHERE template_name = '大挑';

INSERT OR IGNORE INTO process_node_status (template_id, node_name, status_options)
SELECT id, '校赛', '["待评审","已推荐","未推荐"]' FROM process_templates WHERE template_name IN ('国创赛','小挑','三创赛常规赛','三创赛实战赛');
INSERT OR IGNORE INTO process_node_status (template_id, node_name, status_options)
SELECT id, '省赛', '["待评审","已晋级","未晋级"]' FROM process_templates WHERE template_name IN ('国创赛','小挑','三创赛常规赛','三创赛实战赛');
INSERT OR IGNORE INTO process_node_status (template_id, node_name, status_options)
SELECT id, '国赛', '["待评审","已获奖","未获奖"]' FROM process_templates WHERE template_name IN ('国创赛','小挑','三创赛常规赛','三创赛实战赛');

INSERT OR IGNORE INTO process_node_status (template_id, node_name, status_options)
SELECT id, '学生申报', '["已提交","退回修改"]' FROM process_templates WHERE template_name = '大创创新训练';
INSERT OR IGNORE INTO process_node_status (template_id, node_name, status_options)
SELECT id, '导师审核', '["待审核","通过","驳回"]' FROM process_templates WHERE template_name = '大创创新训练';
INSERT OR IGNORE INTO process_node_status (template_id, node_name, status_options)
SELECT id, '学院资格审核', '["待审核","通过","驳回"]' FROM process_templates WHERE template_name = '大创创新训练';
INSERT OR IGNORE INTO process_node_status (template_id, node_name, status_options)
SELECT id, '学院评审答辩', '["待答辩","已评分"]' FROM process_templates WHERE template_name = '大创创新训练';
INSERT OR IGNORE INTO process_node_status (template_id, node_name, status_options)
SELECT id, '学院排序', '["待排序","已推荐","未推荐"]' FROM process_templates WHERE template_name = '大创创新训练';
INSERT OR IGNORE INTO process_node_status (template_id, node_name, status_options)
SELECT id, '学校复审', '["待复审","通过","驳回"]' FROM process_templates WHERE template_name = '大创创新训练';
INSERT OR IGNORE INTO process_node_status (template_id, node_name, status_options)
SELECT id, '立项', '["待立项","已立项","驳回"]' FROM process_templates WHERE template_name = '大创创新训练';
INSERT OR IGNORE INTO process_node_status (template_id, node_name, status_options)
SELECT id, '中期检查', '["待提交","待审核","通过","需整改","不通过"]' FROM process_templates WHERE template_name = '大创创新训练';
INSERT OR IGNORE INTO process_node_status (template_id, node_name, status_options)
SELECT id, '结题验收', '["待提交","待审核","通过","不通过"]' FROM process_templates WHERE template_name = '大创创新训练';

INSERT OR IGNORE INTO process_node_status (template_id, node_name, status_options)
SELECT id, '学生申报', '["已提交","退回修改"]' FROM process_templates WHERE template_name IN ('大创创业训练','大创创业实践');
INSERT OR IGNORE INTO process_node_status (template_id, node_name, status_options)
SELECT id, '双导师审核', '["待审核","通过","驳回"]' FROM process_templates WHERE template_name IN ('大创创业训练','大创创业实践');
INSERT OR IGNORE INTO process_node_status (template_id, node_name, status_options)
SELECT id, '学校统一评审', '["待评审","已评审"]' FROM process_templates WHERE template_name IN ('大创创业训练','大创创业实践');
INSERT OR IGNORE INTO process_node_status (template_id, node_name, status_options)
SELECT id, '学校复审', '["待复审","通过","驳回"]' FROM process_templates WHERE template_name IN ('大创创业训练','大创创业实践');
INSERT OR IGNORE INTO process_node_status (template_id, node_name, status_options)
SELECT id, '立项', '["待立项","已立项","驳回"]' FROM process_templates WHERE template_name IN ('大创创业训练','大创创业实践');
INSERT OR IGNORE INTO process_node_status (template_id, node_name, status_options)
SELECT id, '中期检查', '["待提交","待审核","通过","需整改","不通过"]' FROM process_templates WHERE template_name IN ('大创创业训练','大创创业实践');
INSERT OR IGNORE INTO process_node_status (template_id, node_name, status_options)
SELECT id, '结题验收', '["待提交","待审核","通过","不通过"]' FROM process_templates WHERE template_name IN ('大创创业训练','大创创业实践');

INSERT OR REPLACE INTO award_levels (template_id, level_options)
SELECT id, '["特等奖","一等奖","二等奖","三等奖"]' FROM process_templates WHERE template_name = '大挑';
INSERT OR REPLACE INTO award_levels (template_id, level_options)
SELECT id, '["金奖","银奖","铜奖"]' FROM process_templates WHERE template_name IN ('国创赛','小挑');
INSERT OR REPLACE INTO award_levels (template_id, level_options)
SELECT id, '["特等奖","一等奖","二等奖","三等奖"]' FROM process_templates WHERE template_name IN ('三创赛常规赛','三创赛实战赛');

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
);
CREATE INDEX IF NOT EXISTS idx_jiebang_topics_year_group ON jiebang_topics(year, group_no, topic_no);
CREATE INDEX IF NOT EXISTS idx_jiebang_topics_enabled ON jiebang_topics(year, enabled);
