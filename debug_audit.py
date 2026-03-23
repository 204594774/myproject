
import sqlite3
import json
import requests
from app import app, get_db_connection, ROLES

def debug_audit():
    with app.app_context():
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        
        # 1. Check a project
        print("--- Checking Projects ---")
        projects = conn.execute("SELECT id, title, status, advisor_name, created_by FROM projects").fetchall()
        for p in projects:
            print(f"Project ID: {p['id']}, Title: {p['title']}, Status: {p['status']}, Advisor: {p['advisor_name']}")
            
        # 2. Check Users (Teacher and College Approver)
        print("\n--- Checking Users ---")
        users = conn.execute("SELECT id, username, role, real_name, college FROM users WHERE role IN (?, ?)", (ROLES['TEACHER'], ROLES['COLLEGE_APPROVER'])).fetchall()
        for u in users:
            print(f"User ID: {u['id']}, Username: {u['username']}, Role: {u['role']}, College: {u['college']}")

        # 3. Simulate College Approver Audit
        # Find a project that is advisor_approved
        
        # First, force project 1 to be advisor_approved for testing if it's not
        conn.execute("UPDATE projects SET status = 'advisor_approved' WHERE id = 1")
        conn.commit()
        
        print(f"\n--- Simulating College Approver Audit for Project 1 ---")
        project = conn.execute("SELECT * FROM projects WHERE id = 1").fetchone()
        
        if project:
            approver = conn.execute("SELECT * FROM users WHERE role = ? AND college = ?", (ROLES['COLLEGE_APPROVER'], project['college'])).fetchone()
            
            if approver:
                client = app.test_client()
                with client.session_transaction() as sess:
                    sess['user_id'] = approver['id']
                    sess['role'] = approver['role']
                    sess['college'] = approver['college']
                
                print(f"Approver {approver['username']} attempting to approve...")
                res = client.put(f"/api/projects/{project['id']}/audit", json={'action': 'approve', 'feedback': 'Good'})
                print(f"Response: {res.status_code}, {res.json}")
            else:
                print(f"Approver for college {project['college']} not found!")
        else:
            print("Project 1 not found.")

        conn.close()

if __name__ == "__main__":
    debug_audit()
