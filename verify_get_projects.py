import requests
import json

BASE_URL = 'http://127.0.0.1:5000/api'

def login(username, password):
    session = requests.Session()
    resp = session.post(f'{BASE_URL}/login', json={'username': username, 'password': password})
    if resp.status_code == 200:
        print(f"Login successful for {username}")
        return session
    else:
        print(f"Login failed for {username}: {resp.text}")
        return None

def test_get_projects():
    # Login as student
    session = login('student1', 'student123')
    if not session:
        return

    # Get projects
    resp = session.get(f'{BASE_URL}/projects')
    if resp.status_code == 200:
        projects = resp.json()
        print(f"Projects found: {len(projects)}")
        ids = [p['id'] for p in projects]
        print(f"Project IDs: {ids}")
        if 6 in ids:
            print("FAIL: ID 6 still present!")
        else:
            print("PASS: ID 6 not found.")
    else:
        print(f"Get projects failed: {resp.status_code} {resp.text}")

    # Login as system_admin
    session_admin = login('admin', 'admin123')
    if session_admin:
        resp = session_admin.get(f'{BASE_URL}/projects')
        if resp.status_code == 200:
            projects = resp.json()
            ids = [p['id'] for p in projects]
            print(f"Admin Project IDs: {ids}")
            if 6 in ids:
                print("FAIL: ID 6 still present for Admin!")
            else:
                print("PASS: ID 6 not found for Admin.")

if __name__ == '__main__':
    try:
        test_get_projects()
    except Exception as e:
        print(f"Error: {e}")
