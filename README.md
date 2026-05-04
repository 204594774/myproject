# 高校项目管理系统

基于 Flask + Vue.js 的高校项目申报与审批管理系统，支持创新创业项目、大挑（小挑）、国创赛等多种赛事项目管理。

## 系统地址

- **本地访问**: http://127.0.0.1:5000
- **Swagger API文档**: http://127.0.0.1:5000/apidocs/ (如已配置)

## 快速启动

### 方式一：双击运行
```bash
双击运行 run_app.bat
```

### 方式二：命令行启动
```bash
python app.py
```

### 方式三：使用 run.py
```bash
python run.py
```

## 系统架构

```
new12_backup/
├── app/                    # 应用核心模块
│   ├── auth/              # 认证模块
│   ├── projects/          # 项目管理
│   ├── reviews/           # 评审功能
│   ├── system/            # 系统设置
│   ├── users/             # 用户管理
│   ├── utils/             # 工具类
│   └── schema.sql         # 数据库建表SQL
├── static/                 # 静态资源
│   ├── js/               # 前端Vue代码
│   ├── css/              # 样式文件
│   ├── lib/              # 第三方库
│   └── uploads/           # 上传文件
├── templates/             # HTML模板
├── database.db            # SQLite数据库
├── app.py                 # Flask应用入口
├── config.py              # 配置文件
└── run.py                 # 启动脚本
```

## 角色说明

| 角色 | 说明 | 主要权限 |
|------|------|---------|
| system_admin | 系统管理员 | 全系统管理、用户管理、系统设置 |
| project_admin | 项目管理员 | 项目管理、赛事管理 |
| college_approver | 学院审批者 | 学院级项目审批、评委分配 |
| school_approver | 学校审批者 | 校级/省级/国家级项目终审 |
| judge | 评委 | 评审分配的项目 |
| teacher | 指导老师 | 指导学生项目、审核材料 |
| student | 学生 | 申报项目、提交材料 |

## 默认账号

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 系统管理员 | admin | admin123 |
| 项目管理员 | proj_admin | admin123 |
| 学院审批者 | col_approver | admin123 |
| 学校审批者 | sch_approver | admin123 |
| 评委1 | judge1 | admin123 |
| 评委2 | judge2 | admin123 |
| 评委3 | judge3 | admin123 |
| 教师 | teacher1 | teacher123 |
| 学生 | student1 | student123 |

## 核心功能

### 1. 项目管理
- **项目申报**: 学生可申报创新创业项目、赛事项目（大挑、小挑、国创赛、三创赛等）
- **三级审批**: 导师审核 → 学院审批 → 学校终审
- **过程管理**: 中期检查、结项报告提交与审核
- **项目评级**: 国家级、省级、校级

### 2. 大挑功能
- 支持大挑（挑战杯）专项流程
- 院级评审 → 校级评审 → 省级推荐 → 国家级评选
- 专门的评委分配和评审任务管理
- 评审标准和评分指标

### 3. 评审系统
- **评委任务**: 评委可查看分配的评审任务
- **在线评分**: 支持多维度评分和评语
- **评审历史**: 记录所有评审记录

### 4. 赛事管理
- 创建和管理各类赛事（大挑、小挑、国创赛、三创赛等）
- 赛事报名与项目关联
- 赛事状态管理（进行中、已结束）

### 5. 文件管理
- 项目申报书上传
- 中期/结项报告上传
- 附件管理

### 6. 通知系统
- 站内通知
- 审批进度通知
- 评审任务通知

## 项目类型

| 类型 | 说明 | 流程 |
|------|------|------|
| innovation | 创新训练项目 | 导师→学院→学校 |
| entrepreneurship | 创业训练项目 | 导师→学院→学校 |
| 大挑 | 挑战杯专项 | 院赛→校赛→省赛→国赛 |
| 小挑 | 挑战杯创业专项 | 院赛→校赛→省赛→国赛 |
| 国创赛 | 国家级大学生创新创业大赛 | 校赛→省赛→国赛 |
| 三创赛 | 电子商务创新创意创业大赛 | 校赛→省赛→国赛 |

## 项目状态

| 状态 | 说明 |
|------|------|
| draft | 草稿 |
| pending | 待导师审核 |
| advisor_approved | 导师已通过 |
| under_review | 评审中 |
| college_approved | 学院已通过 |
| school_approved | 学校已通过 |
| rated | 已评级 |
| rejected | 已驳回 |
| midterm_submitted | 中期待审核 |
| midterm_approved | 中期已通过 |
| conclusion_submitted | 结项待审核 |
| finished | 已结项 |

## API 接口

主要接口前缀: `/api/`

| 接口 | 方法 | 说明 |
|------|------|------|
| /api/login | POST | 用户登录 |
| /api/logout | POST | 用户登出 |
| /api/me | GET/PUT | 个人信息 |
| /api/projects | GET/POST | 项目列表/创建 |
| /api/projects/<id> | GET/PUT/DELETE | 项目详情/更新/删除 |
| /api/projects/<id>/audit | PUT | 项目审批 |
| /api/projects/<id>/review | POST | 项目评审 |
| /api/projects/<id>/midterm | POST | 提交中期报告 |
| /api/projects/<id>/conclusion | POST | 提交结项报告 |
| /api/users | GET/POST | 用户列表/创建 |
| /api/competitions | GET/POST | 赛事列表/创建 |
| /api/reviews/tasks | GET | 评审任务列表 |
| /api/notifications | GET | 通知列表 |
| /api/announcements | GET/POST | 公告列表/发布 |
| /api/system/stats | GET | 系统统计 |
| /api/common/upload | POST | 文件上传 |

## 技术栈

- **后端**: Flask (Python)
- **前端**: Vue.js 3 + Element Plus
- **数据库**: SQLite
- **图表**: ECharts
- **文件处理**: python-docx

## 数据库

数据库文件: `database.db`

核心表结构:
- `users` - 用户表
- `projects` - 项目表
- `project_members` - 项目成员表
- `project_reviews` - 评审记录表
- `review_tasks` - 评审任务表
- `competitions` - 赛事表
- `notifications` - 通知表
- `announcements` - 公告表
- `system_settings` - 系统设置表
- `system_logs` - 系统日志表
- `project_files` - 项目文件表
- `process_templates` - 流程模板表
- `process_node_status` - 流程节点状态表

## 注意事项

1. 首次使用请确保数据库已初始化
2. 默认端口: 5000
3. 调试模式: 已开启 (debug=True)
4. 上传文件保存在 `static/uploads/` 目录
5. 日志文件保存在 `logs/` 目录
