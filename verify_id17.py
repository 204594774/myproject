import requests
import json

BASE_URL = 'http://127.0.0.1:5000'

def login(username, password):
    s = requests.Session()
    resp = s.post(f'{BASE_URL}/api/login', json={'username': username, 'password': password})
    if resp.status_code != 200:
        print(f"Login failed: {resp.text}")
        return None
    return s

def test_update_17():
    session = login('student1', 'student123')
    if not session: return

    print("Checking if ID 17 exists via GET...")
    resp = session.get(f'{BASE_URL}/api/projects/17')
    print(f"GET Status: {resp.status_code}")
    if resp.status_code == 200:
        print("Project 17 found.")
    else:
        print(f"Project 17 NOT found via API. Response: {resp.text}")
        return

    print("Attempting PUT update on ID 17...")
    payload = {
        "id": 17,
        "title": "1 - 参赛项目 - Updated",
        "project_type": "entrepreneurship_training",
        "members": [],
        "extra_info": {}
    }
    
    resp = session.put(f'{BASE_URL}/api/projects/17', json=payload)
    print(f"PUT Status: {resp.status_code}")
    print(f"PUT Response: {resp.text}")

if __name__ == '__main__':
    test_update_17()
