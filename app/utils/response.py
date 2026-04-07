from flask import jsonify

def success(data=None, message='操作成功', code=200):
    return jsonify({
        'code': code,
        'message': message,
        'data': {} if data is None else data
    }), code

def fail(message='操作失败', code=400, data=None):
    return jsonify({
        'code': code,
        'message': message,
        'error': message,
        'data': {} if data is None else data
    }), code
