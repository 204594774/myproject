from flask import Blueprint, jsonify, request
from app.utils.response import fail

errors_bp = Blueprint('errors', __name__)

@errors_bp.app_errorhandler(404)
def not_found_error(error):
    # 忽略以 /apidocs 或者 /flasgger 开头的请求，让 flasgger 自己处理
    if request.path.startswith('/apidocs') or request.path.startswith('/flasgger'):
        return error
    return fail('资源未找到', 404)

@errors_bp.app_errorhandler(500)
def internal_error(error):
    return fail('服务器内部错误', 500)

@errors_bp.app_errorhandler(403)
def forbidden_error(error):
    return fail('无权限访问', 403)

@errors_bp.app_errorhandler(401)
def unauthorized_error(error):
    return fail('未登录或会话已过期', 401)
