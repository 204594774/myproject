import requests
import json
import sqlite3

BASE_URL = 'http://127.0.0.1:5000'

def test_audit():
    # 1. Login as College Approver (col_approver / admin123)
    # Check database.py for credentials
    session = requests.Session()
    resp = session.post(f'{BASE_URL}/api/login', json={
        'username': 'col_approver',
        'password': 'admin123'
    })
    
    if resp.status_code != 200:
        print(f"Login failed: {resp.status_code}, {resp.text}")
        # Try to create if not exists (though default data should have it)
        return

    print("Login as col_approver: SUCCESS")
    
    # 2. Get projects pending college approval
    # Status should be 'advisor_approved' (or 'pending' if no advisor needed, but usually advisor_approved)
    # Let's verify what projects are available
    resp = session.get(f'{BASE_URL}/api/projects')
    projects = resp.json()
    
    target_project = None
    for p in projects:
        if p['status'] in ['advisor_approved', 'pending']:
            target_project = p
            break
            
    if not target_project:
        print("No project found for college audit. Creating a test project first...")
        # Login as student to create one
        student_session = requests.Session()
        student_session.post(f'{BASE_URL}/api/login', json={'username': 'student1', 'password': 'student123'})
        
        # Create project
        create_resp = student_session.post(f'{BASE_URL}/api/projects', json={
            'title': 'Test Project for Audit',
            'project_type': 'innovation',
            'level': 'school',
            'year': '2025',
            'leader_name': 'Student One',
            'members': []
        })
        new_pid = create_resp.json().get('project_id')
        print(f"Created test project ID: {new_pid}")
        
        # Advisor approve it first (if needed) - let's cheat and update DB directly to advisor_approved
        conn = sqlite3.connect('database.db')
        conn.execute("UPDATE projects SET status = 'advisor_approved', college='计算机学院' WHERE id = ?", (new_pid,))
        conn.commit()
        conn.close()
        
        target_project = {'id': new_pid, 'title': 'Test Project for Audit'}
    
    print(f"Attempting to audit project ID: {target_project['id']}")
    
    # 3. Perform Audit
    audit_resp = session.put(f'{BASE_URL}/api/projects/{target_project["id"]}/audit', json={
        'action': 'approve',
        'feedback': 'Approved by script'
    })
    
    print(f"Audit response code: {audit_resp.status_code}")
    print(f"Audit response text: {audit_resp.text}")

if __name__ == '__main__':
    test_audit()
