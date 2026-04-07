from app import create_app
import os

app = create_app()

if __name__ == '__main__':
    # 确保日志目录存在
    if not os.path.exists('logs'):
        os.makedirs('logs')
        
    # 端口可按需调整：避免与其他项目冲突
    app.run(debug=True, port=5001, host='0.0.0.0')
