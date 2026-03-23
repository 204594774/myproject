import requests
import json
import sqlite3

BASE_URL = 'http://127.0.0.1:5000/api'
SESSION = requests.Session()

def login(username, password):
    try:
        res = SESSION.post(f'{BASE_URL}/login', json={'username': username, 'password': password})
        if res.status_code == 200:
            print(f"Login as {username}: SUCCESS")
            return res.json()['user']
        else:
            print(f"Login as {username}: FAILED - {res.status_code} {res.text}")
            return None
    except Exception as e:
        print(f"Login error: {e}")
        return None

def test_put_id_10():
    print("\n--- Testing PUT ID 10 ---")
    # Login as admin to ensure permissions (or teacher/student if we knew who owns it)
    # But since we don't know who owns 10, admin is best bet (or student1)
    # Actually, update_project checks permissions. If 10 doesn't exist, it should 404 regardless of permission?
    # No, it checks role first.
    user = login('student1', 'student123') 
    if not user: return

    # Try to PUT to 10
    payload = {
        'title': 'Test ID 10 Update',
        'project_type': 'innovation',
        'extra_info': {}
    }
    
    res = SESSION.put(f'{BASE_URL}/projects/10', json=payload)
    print(f"PUT /api/projects/10 Response: {res.status_code}")
    print(f"Response Body: {res.text}")

    if res.status_code == 200:
        print("!!! PUT ID 10 Succeeded! DB check was wrong? !!!")
    elif res.status_code == 404:
        print("Confirmed: ID 10 Not Found (404)")
    else:
        print(f"Other error: {res.status_code}")

def test_get_id_17():
    print("\n--- Testing GET ID 17 ---")
    res = SESSION.get(f'{BASE_URL}/projects/17')
    print(f"GET /api/projects/17 Response: {res.status_code}")
    print(f"Response Body: {res.text}")

def check_db_direct():
    print("\n--- Direct DB Check ---")
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM projects WHERE id IN (6, 10, 13, 17)")
        rows = cursor.fetchall()
        print(f"IDs found in DB: {rows}")
        conn.close()
    except Exception as e:
        print(f"DB Check Error: {e}")

if __name__ == '__main__':
    test_put_id_10()
    test_get_id_17()
    check_db_direct()
