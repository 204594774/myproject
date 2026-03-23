import sqlite3
from werkzeug.security import generate_password_hash

def fix_data():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # 1. Update College Admin's college
    print("Updating College Admin...")
    cursor.execute("UPDATE users SET college = '计算机学院（人工智能学院）' WHERE username = 'college'")
    
    # 2. Check if '黄老师' exists, if not create
    cursor.execute("SELECT id FROM users WHERE real_name = '黄老师'")
    if not cursor.fetchone():
        print("Creating teacher '黄老师'...")
        pwd = generate_password_hash('123456')
        cursor.execute("INSERT INTO users (username, password, role, real_name, college) VALUES (?, ?, ?, ?, ?)",
                      ('teacher_huang', pwd, 'teacher', '黄老师', '计算机学院（人工智能学院）'))
    
    conn.commit()
    conn.close()
    print("Data fixed.")

if __name__ == '__main__':
    fix_data()
