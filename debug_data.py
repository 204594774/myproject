
import sqlite3

def check_data():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    
    # 1. Check Project
    p = conn.execute('SELECT * FROM projects WHERE id=17').fetchone()
    print(f"Project 17 CreatedBy: {p['created_by']} (Type: {type(p['created_by'])})")
    
    # 2. Check User
    u = conn.execute('SELECT * FROM users WHERE username="student1"').fetchone()
    print(f"User student1 ID: {u['id']} (Type: {type(u['id'])})")
    print(f"User RealName: '{u['real_name']}'")
    print(f"User Identity: '{u['identity_number']}'")
    
    # 3. Check Members
    members = conn.execute('SELECT * FROM project_members WHERE project_id=17').fetchall()
    print("\nProject Members:")
    for m in members:
        print(f" - ID={m['id']}, Name='{m['name']}', StudentID='{m['student_id']}', IsLeader={m['is_leader']}")

    conn.close()

if __name__ == '__main__':
    check_data()
