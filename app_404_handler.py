
@app.errorhandler(404)
def page_not_found(e):
    print(f"DEBUG: 404 Error on request: {request.method} {request.path}")
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Resource not found', 'path': request.path}), 404
    return "404 Not Found", 404
