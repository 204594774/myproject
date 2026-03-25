import logging
from logging.handlers import RotatingFileHandler
import os
from config import get_config

def setup_logging(app):
    """
    配置系统日志：同时输出到控制台和旋转日志文件
    """
    config = get_config()
    
    # 确保日志目录存在
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    log_file = os.path.join(log_dir, 'app.log')
    
    # 日志格式定义
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    
    # 1. 配置文件日志处理器 (按大小切割，保留5个备份)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=1024*1024*5, backupCount=5, encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG if config.DEBUG else logging.INFO)
    
    # 2. 配置控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # 3. 将处理器添加到 Flask app.logger
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    
    # 设置根日志级别
    app.logger.setLevel(logging.DEBUG if config.DEBUG else logging.INFO)
    
    # 移除 Flask 默认的处理器以避免重复输出
    # app.logger.propagate = False
    
    app.logger.info(f"Logging system initialized. Log file: {log_file}")
    
    return app.logger
