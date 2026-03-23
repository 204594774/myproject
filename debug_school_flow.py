import sqlite3
import json
import requests
from app import app, ROLES

def test_school_flow():
    # Setup
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Ensure users exist
    # Student
    cursor.execute("INSERT OR IGNORE INTO users (username, password, role, real_name, college) VALUES ('stu_test', '123', 'student', 'Student Test', 'Computer College')")
    stu_id = cursor.execute("SELECT id FROM users WHERE username='stu_test'").fetchone()[0]
    
    # Advisor
    cursor.execute("INSERT OR IGNORE INTO users (username, password, role, real_name, college) VALUES ('adv_test', '123', 'teacher', 'Advisor Test', 'Computer College')")
    adv_id = cursor.execute("SELECT id FROM users WHERE username='adv_test'").fetchone()[0]
    
    # College Approver
    cursor.execute("INSERT OR IGNORE INTO users (username, password, role, real_name, college) VALUES ('col_test', '123', 'college_approver', 'College Admin', 'Computer College')")
    col_id = cursor.execute("SELECT id FROM users WHERE username='col_test'").fetchone()[0]
    
    # School Approver
    cursor.execute("INSERT OR IGNORE INTO users (username, password, role, real_name) VALUES ('sch_test', '123', 'school_approver', 'School Admin')")
    sch_id = cursor.execute("SELECT id FROM users WHERE username='sch_test'").fetchone()[0]
    
    conn.commit()
    
    # 1. Create Project
    print(f"Creating project by Student {stu_id}...")
    cursor.execute('''
        INSERT INTO projects (title, created_by, status, college, advisor_name) 
        VALUES ('Test School Flow', ?, 'pending', 'Computer College', 'Advisor Test')
    ''', (stu_id,))
    pid = cursor.lastrowid
    conn.commit()
    print(f"Project {pid} created.")
    
    # 2. Advisor Approve
    print("Advisor approving...")
    # Simulate API call logic locally
    cursor.execute("UPDATE projects SET status='advisor_approved' WHERE id=?", (pid,))
    # Notify College
    cursor.execute("INSERT INTO notifications (user_id, title, content, type) VALUES (?, 'Test', 'Test Content', 'approval')", (col_id,))
    conn.commit()
    
    # 3. College Approve
    print("College approving...")
    cursor.execute("UPDATE projects SET status='college_approved' WHERE id=?", (pid,))
    conn.commit()
    
    # NOW THE CRITICAL PART: Trigger the notification logic manually as app.py does
    print("Triggering School Notification...")
    # Logic from app.py:
    approvers = cursor.execute('SELECT id FROM users WHERE role = ?', ('school_approver',)).fetchall()
    print(f"Found {len(approvers)} school approvers: {approvers}")
    
    for approver in approvers:
        cursor.execute('INSERT INTO notifications (user_id, title, content, type) VALUES (?, ?, ?, ?)',
                      (approver[0], '新项目待学校审批', f"项目 Test School Flow 已通过学院审核，请学校审批", 'approval'))
        print(f"Notification inserted for user {approver[0]}")
        
    conn.commit()
    
    # 4. Check Result
    notifs = cursor.execute("SELECT * FROM notifications WHERE user_id=?", (sch_id,)).fetchall()
    print(f"School Approver {sch_id} Notifications: {len(notifs)}")
    for n in notifs:
        print(f" - {n[2]}: {n[3]}")
        
    conn.close()

if __name__ == '__main__':
    test_school_flow()
