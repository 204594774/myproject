import requests
import json

BASE_URL = 'http://127.0.0.1:5000'

def test_api():
    session = requests.Session()
    
    # 1. Login as student1
    print("Logging in as student1...")
    resp = session.post(f'{BASE_URL}/api/login', json={'username': 'student1', 'password': 'student123'})
    print(f"Login status: {resp.status_code}")
    if resp.status_code != 200:
        print("Login failed")
        return

    # 2. Get projects
    print("Fetching projects...")
    resp = session.get(f'{BASE_URL}/api/projects')
    print(f"Projects status: {resp.status_code}")
    if resp.status_code == 200:
        projects = resp.json()
        print(f"Projects count: {len(projects)}")
        print(json.dumps(projects, indent=2, ensure_ascii=False))
    else:
        print(resp.text)

if __name__ == '__main__':
    test_api()
