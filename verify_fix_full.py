import sqlite3
import requests
import json

BASE_URL = 'http://127.0.0.1:5000'

def check_everything():
    print("--- STARTING COMPREHENSIVE CHECK ---")
    
    # 1. Database Checks
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    
    # Check User
    user = conn.execute('SELECT * FROM users WHERE id = 7').fetchone()
    print(f"[DB] User 7: username={user['username']}, role={user['role']}, identity_number={user['identity_number']}")
    if user['identity_number'] != '202221091347':
        print("FAIL: User identity_number mismatch!")
    else:
        print("PASS: User identity_number correct.")

    # Check Project
    project = conn.execute('SELECT * FROM projects WHERE id = 17').fetchone()
    print(f"[DB] Project 17: status={project['status']}, created_by={project['created_by']}")
    if project['status'] != 'pending':
        print("FAIL: Project status is not pending!")
    else:
        print("PASS: Project status is pending.")
        
    if project['created_by'] != 7:
        print(f"WARN: Project created_by is {project['created_by']}, not 7. Ownership check will fail, falling back to Leader check.")
    else:
        print("PASS: Project created_by is 7 (Owner).")

    # Check Members
    members = conn.execute('SELECT * FROM project_members WHERE project_id = 17').fetchall()
    leader_found = False
    for m in members:
        print(f"[DB] Member: name={m['name']}, is_leader={m['is_leader']}, student_id={m['student_id']}")
        if m['is_leader'] and str(m['student_id']) == '202221091347':
            leader_found = True
            
    if leader_found:
        print("PASS: Leader member found with correct ID.")
    else:
        print("FAIL: No leader member with correct ID found!")

    conn.close()

    # 2. API Login Check
    print("\n--- API CHECKS ---")
    s = requests.Session()
    try:
        resp = s.post(f'{BASE_URL}/api/login', json={'username': 'student1', 'password': 'student123'})
        if resp.status_code != 200:
            print(f"FAIL: Login failed: {resp.text}")
            return
        print(f"PASS: Login successful. Cookies: {s.cookies.get_dict()}")
        
        # 3. API Get Project Check
        resp = s.get(f'{BASE_URL}/api/projects/17')
        if resp.status_code != 200:
            print(f"FAIL: Get project failed: {resp.text}")
            return
            
        data = resp.json()
        print(f"[API] Project Status: {data.get('status')}")
        
        # Check permission via simulated edit (Dry run - just check if we get 403 or 400)
        # We'll try to send the EXACT same data back to see if it accepts it
        
        payload = data
        # Fix potential payload issues
        if 'created_at' in payload: del payload['created_at']
        if 'updated_at' in payload: del payload['updated_at']
        if 'files' in payload: del payload['files']
        if 'reviews' in payload: del payload['reviews']
        
        # Ensure extra_info is dict
        if isinstance(payload.get('extra_info'), str):
             import json
             payload['extra_info'] = json.loads(payload['extra_info'])
             
        print(f"Attempting update with current project data...")
        resp = s.put(f'{BASE_URL}/api/projects/17', json=payload)
        print(f"[API] Update Response: {resp.status_code} - {resp.text}")
        
        if resp.status_code == 200:
            print("PASS: Update successful!")
        else:
            print("FAIL: Update failed!")

    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == '__main__':
    check_everything()
