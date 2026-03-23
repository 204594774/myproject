import requests
import sqlite3

BASE_URL = 'http://127.0.0.1:5000'

def set_project_status(status):
    conn = sqlite3.connect('database.db')
    conn.execute('UPDATE projects SET status=? WHERE id=17', (status,))
    conn.commit()
    conn.close()
    print(f"Set project 17 status to: {status}")

def attempt_edit(expected_status_code, scenario_name):
    print(f"\n--- Testing: {scenario_name} ---")
    s = requests.Session()
    # Login
    resp = s.post(f'{BASE_URL}/api/login', json={'username': 'student1', 'password': 'student123'})
    if resp.status_code != 200:
        print("Login failed")
        return
    
    # Get Data
    resp = s.get(f'{BASE_URL}/api/projects/17')
    if resp.status_code != 200:
        print("Get project failed")
        return
    data = resp.json()
    
    # Edit
    resp = s.put(f'{BASE_URL}/api/projects/17', json=data)
    print(f"Update Response: {resp.status_code} (Expected: {expected_status_code})")
    
    if resp.status_code == expected_status_code:
        print("PASS")
    else:
        print(f"FAIL: {resp.text}")

if __name__ == '__main__':
    # 1. Test college_approved (Should be Allowed -> 200)
    set_project_status('college_approved')
    attempt_edit(200, "Edit in 'college_approved'")

    # 2. Test school_approved (Should be Forbidden -> 400)
    set_project_status('school_approved')
    attempt_edit(400, "Edit in 'school_approved' (Review Stage)")
    
    # Reset to pending for user
    set_project_status('pending')
