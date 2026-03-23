from werkzeug.security import generate_password_hash
import sqlite3
import os

db_path = r'D:\桌面\new11\database.db'
conn = sqlite3.connect(db_path)

def reset_pwd(username, pwd):
    hashed = generate_password_hash(pwd)
    conn.execute('UPDATE users SET password = ? WHERE username = ?', (hashed, username))
    print(f"Reset password for {username}")

reset_pwd('admin', 'admin123')
reset_pwd('col_approver', 'admin123')
reset_pwd('sch_approver', 'admin123')
reset_pwd('teacher1', 'teacher123')

conn.commit()
conn.close()
