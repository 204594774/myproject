import sqlite3
import json
import os

def debug_school_flow_full():
    db_path = 'database.db'
    if not os.path.exists(db_path):
        print("Database not found!")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Clean up previous test data
    cursor.execute("DELETE FROM projects WHERE title = 'School Flow Test Project'")
    cursor.execute("DELETE FROM notifications WHERE title LIKE '%School Flow Test Project%'")
    conn.commit()

    print("--- 1. Creating Project (Student) ---")
    # Create a project
    cursor.execute("""
        INSERT INTO projects (title, status, created_by, college, project_type, level, year) 
        VALUES ('School Flow Test Project', 'submitted', 1, 'Computer Science', 'innovation', 'school', '2024')
    """)
    pid = cursor.lastrowid
    print(f"Project created with ID: {pid}")

    # 2. Advisor Approval
    print("\n--- 2. Advisor Approval (Teacher) ---")
    # Simulate Teacher approving
    cursor.execute("UPDATE projects SET status = 'advisor_approved' WHERE id = ?", (pid,))
    print("Project status updated to 'advisor_approved'")

    # 3. College Approval
    print("\n--- 3. College Approval (College Approver) ---")
    # Simulate College Approver approving
    cursor.execute("UPDATE projects SET status = 'college_approved' WHERE id = ?", (pid,))
    print("Project status updated to 'college_approved'")

    # Trigger Notification logic manually (mimicking app.py)
    # Fetch School Approvers
    school_approvers = cursor.execute("SELECT id, username FROM users WHERE role = 'school_approver'").fetchall()
    print(f"Found {len(school_approvers)} school approvers: {[dict(row) for row in school_approvers]}")

    for approver in school_approvers:
        print(f"Inserting notification for User {approver['id']} ({approver['username']})...")
        cursor.execute("""
            INSERT INTO notifications (user_id, title, content, type) 
            VALUES (?, ?, ?, ?)
        """, (approver['id'], '新项目待学校审批', f"项目 School Flow Test Project 已通过学院审核，请学校审批", 'approval'))
    conn.commit()

    # 4. Verify Notification
    print("\n--- 4. Verifying Notifications ---")
    for approver in school_approvers:
        notifs = cursor.execute("SELECT * FROM notifications WHERE user_id = ? ORDER BY id DESC LIMIT 1", (approver['id'],)).fetchall()
        if notifs:
            print(f"User {approver['username']} has notification: {notifs[0]['title']} - {notifs[0]['content']}")
        else:
            print(f"FAILURE: User {approver['username']} has NO notifications!")

    # 5. Verify Project Visibility (Simulating API Query)
    print("\n--- 5. Verifying Project Visibility (API Query) ---")
    
    # Simulate the query used in app.py for SCHOOL_APPROVER
    query = "SELECT id, title, status FROM projects WHERE 1=1"
    # Logic from app.py
    query += " AND status IN ('college_approved', 'school_approved', 'rated', 'midterm_submitted', 'midterm_approved', 'conclusion_submitted', 'finished', 'midterm_college_approved', 'conclusion_college_approved')"
    query += " AND id = ?"
    
    project_visible = cursor.execute(query, (pid,)).fetchone()
    
    if project_visible:
        print(f"SUCCESS: Project {pid} is VISIBLE to School Approver. Status: {project_visible['status']}")
    else:
        print(f"FAILURE: Project {pid} is NOT VISIBLE to School Approver!")

    conn.close()

if __name__ == '__main__':
    debug_school_flow_full()
