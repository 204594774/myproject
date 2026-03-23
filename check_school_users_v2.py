
import sqlite3

def check_users():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    users = cursor.execute("SELECT id, username, role, college FROM users WHERE role = 'school_approver'").fetchall()
    print(f"School Approvers: {[dict(u) for u in users]}")
    
    conn.close()

if __name__ == '__main__':
    check_users()
