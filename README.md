# 高校项目管理系统 (University Project Management System)

本项目是一个基于 Flask 的高校项目申报与审批管理系统，旨在简化高校内部项目的申报、审核、评审及后期管理流程。本系统专为课程设计（Course Design）优化，包含了完整的工程化实践与答辩亮点。

## 🚀 答辩亮点 (Defense Highlights)

| 特性 | 实现方式 | 优化价值 |
| :--- | :--- | :--- |
| **模块化架构** | 使用 Flask Blueprints 拆分模块 | 彻底解决 `app.py` 臃肿问题，解耦业务逻辑，易于扩展。 |
| **交互式文档** | 集成 Flask-RESTX (Swagger) | 访问 `/swagger/` 即可查看可视化接口文档，展现规范的 API 设计能力。 |
| **工程化配置** | 独立 `config.py` + 环境隔离 | 消除硬编码，支持开发（Dev）与生产（Prod）环境一键切换。 |
| **统一响应规范** | 封装 `success`/`fail` 工具函数 | 确保前后端交互格式一致，提升系统健壮性与调试效率。 |
| **精细化权限** | `@login_required` / `@role_required` | 使用装饰器实现角色级权限控制，代码优雅且安全。 |
| **健壮的日志** | RotatingFileHandler 旋转日志 | 记录关键操作（登录、申报、审批），体现系统可监控性与问题排查能力。 |

## 📁 目录结构

```
myproject/
├── app/                  # 应用核心目录
│   ├── auth/             # 认证模块 (登录/注册/个人信息)
│   ├── projects/         # 项目管理 (申报/三级审批/评审)
│   ├── users/            # 用户管理 (权限/账号审批)
│   ├── system/           # 系统功能 (公告/赛事/日志/统计)
│   ├── utils/            # 工具类 (数据库/权限装饰器/响应/日志)
│   ├── errors/           # 异常处理模块
│   ├── schema.sql        # 数据库建表 SQL
│   └── __init__.py       # App 工厂 (包含 Swagger 配置)
├── logs/                 # 运行日志目录
├── static/               # 静态资源 (Vue/ElementPlus/Uploads)
├── templates/            # HTML 模板
├── config.py             # 全局配置管理
├── database.db           # SQLite 数据库
├── run.py                # 应用启动入口
└── requirements.txt      # 依赖清单
```

## 🛠️ 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 初始化数据库 (包含预设演示数据)
```bash
python -c "from app.utils.db import init_db; init_db()"
```

### 3. 启动应用
```bash
python run.py
```
- **系统首页**: [http://127.0.0.1:5001](http://127.0.0.1:5001)
- **API 文档**: [http://127.0.0.1:5001/apidocs/](http://127.0.0.1:5001/apidocs/)

## 📝 核心业务流程演示

1. **学生申报**: 登录学生账号 -> 填写项目书（支持名称去重、限额申报校验）。
2. **导师审核**: 导师账号登录 -> 审核学生提交的指导申请。
3. **院系审批**: 学院审批者登录 -> 进行院级立项审批。
4. **学校终审**: 学校审批者登录 -> 完成最终立项，状态变为“已立项”。
5. **过程管理**: 学生提交中期报告/结题报告 -> 各级在线审核附件。

## 🔐 默认账户

| 角色 | 用户名 | 密码 |
| :--- | :--- | :--- |
| **系统管理员** | admin | admin123 |
| **学生** | student1 | student123 |
| **指导老师** | teacher1 | teacher123 |
