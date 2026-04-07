from flask import Flask, Blueprint, make_response
import os
from config import get_config
from flasgger import Swagger

def create_app():
    config = get_config()
    
    app = Flask(__name__, 
                static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static'),
                template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates'))
    
    app.config.from_object(config)
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.jinja_env.auto_reload = True
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    
    # Swagger 文档配置 (Flasgger)
    app.config['SWAGGER'] = {
        'title': '高校项目管理系统 API 文档',
        'uiversion': 3,
        'description': '课程设计 - 项目申报/审批/管理全流程接口',
        'version': '1.0'
    }
    # 这里我们不用 specs_route 去覆盖默认的 ui 路由
    swagger = Swagger(app)
    
    # 设置日志
    from .utils.logs import setup_logging
    setup_logging(app)
    
    # 初始化数据库相关（在 request 结束时关闭连接）
    from .utils.db import close_db, ensure_db_schema
    ensure_db_schema()
    app.teardown_appcontext(close_db)
    
    # 注册蓝图
    from .auth.views import auth_bp
    from .projects.views import projects_bp
    from .users.views import users_bp
    from .system.views import system_bp
    from .process.views import process_template_bp
    from .reviews.views import reviews_bp
    from .errors.handlers import errors_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(process_template_bp)
    app.register_blueprint(reviews_bp)
    app.register_blueprint(errors_bp)
    
    # 首页路由
    @app.route('/')
    def index():
        from flask import render_template
        resp = make_response(render_template('index.html'))
        resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        resp.headers['Pragma'] = 'no-cache'
        return resp
        
    return app
