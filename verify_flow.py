import requests
import json

BASE_URL = 'http://127.0.0.1:5000/api'
SESSION = requests.Session()

def login(username, password):
    print(f"Logging in as {username}...")
    res = SESSION.post(f'{BASE_URL}/login', json={'username': username, 'password': password})
    if res.status_code == 200:
        print(f"  Success! Role: {res.json()['user']['role']}")
        return True
    else:
        print(f"  Failed: {res.text}")
        return False

def create_project(title):
    print(f"Creating project '{title}'...")
    data = {
        'title': title,
        'project_type': 'innovation',
        'level': 'school',
        'year': '2025',
        'members': []
    }
    res = SESSION.post(f'{BASE_URL}/projects', json=data)
    if res.status_code == 200:
        pid = res.json()['project_id']
        print(f"  Success! ID: {pid}")
        return pid
    else:
        print(f"  Failed: {res.text}")
        return None

def audit_project(pid, action, role_name):
    print(f"Auditing project {pid} as {role_name} -> {action}...")
    res = SESSION.put(f'{BASE_URL}/projects/{pid}/audit', json={'action': action, 'feedback': 'Good'})
    if res.status_code == 200:
        print(f"  Success!")
    else:
        print(f"  Failed: {res.text}")

def review_project(pid):
    print(f"Reviewing project {pid}...")
    res = SESSION.post(f'{BASE_URL}/projects/{pid}/review', json={'score': 95, 'comment': 'Excellent'})
    if res.status_code == 200:
        print(f"  Success!")
    else:
        print(f"  Failed: {res.text}")

def check_status(pid, expected_status):
    print(f"Checking status of {pid}...")
    res = SESSION.get(f'{BASE_URL}/projects/{pid}')
    if res.status_code == 200:
        status = res.json()['status']
        print(f"  Current: {status}, Expected: {expected_status}")
        if status == expected_status:
             print("  [PASS]")
        else:
             print("  [FAIL]")
    else:
        print(f"  Failed to get project: {res.text}")

def run_test():
    # 1. Login as Student
    if not login('student1', 'student123'): return
    
    # 2. Create Project
    pid = create_project('Test Innovation Project')
    if not pid: return
    
    check_status(pid, 'pending')
    
    # 3. College Approval
    if not login('col_approver', 'admin123'): return
    audit_project(pid, 'approve', 'College Approver')
    check_status(pid, 'college_approved')
    
    # 4. School Approval
    if not login('sch_approver', 'admin123'): return
    audit_project(pid, 'approve', 'School Approver')
    check_status(pid, 'school_approved')
    
    # 5. Judge Review
    if not login('judge1', 'admin123'): return
    review_project(pid)
    check_status(pid, 'rated')

if __name__ == '__main__':
    try:
        run_test()
    except Exception as e:
        print(f"Error: {e}")
