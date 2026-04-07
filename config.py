import os
from dotenv import load_dotenv

load_dotenv()  # 加载 .env 文件（可选）

class Config:
    # 基础配置
    SECRET_KEY = os.getenv('SECRET_KEY', 'your_secret_key')
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'static', 'uploads')
    WATERMARK_SCHOOL_NAME = os.getenv('WATERMARK_SCHOOL_NAME', 'XX大学')
    
    # 项目管理相关配置
    GHOST_PROJECT_IDS = set() # 已清除硬编码的限制 ID
    
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

class DevConfig(Config):
    DEBUG = True
    LOG_LEVEL = 'DEBUG'
    SEND_FILE_MAX_AGE_DEFAULT = 0
    TEMPLATES_AUTO_RELOAD = True

class ProdConfig(Config):
    DEBUG = False
    LOG_LEVEL = 'INFO'
    # 生产环境建议从环境变量读取
    SECRET_KEY = os.getenv('SECRET_KEY')

config_map = {
    'dev': DevConfig,
    'prod': ProdConfig,
    'default': DevConfig
}

def get_config():
    env = os.getenv('FLASK_ENV', 'dev')
    return config_map.get(env, config_map['default'])
