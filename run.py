from app import create_app
import os

app = create_app()

if __name__ == '__main__':
    # 确保日志目录存在
    if not os.path.exists('logs'):
        os.makedirs('logs')
        
    app.run(debug=True, port=5001)
