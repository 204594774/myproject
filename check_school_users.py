import sqlite3

def check_users():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, role FROM users WHERE role = 'school_approver'")
    users = cursor.fetchall()
    print("School Approvers:", users)
    
    cursor.execute("SELECT id, username, role FROM users")
    all_users = cursor.fetchall()
    print("All Users count:", len(all_users))
    conn.close()

if __name__ == '__main__':
    check_users()
