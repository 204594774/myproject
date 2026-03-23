import requests
import json

BASE_URL = 'http://127.0.0.1:5000'

def test_ghost_project(username, password):
    print(f"\n--- Testing for user: {username} ---")
    s = requests.Session()
    
    # Login
    resp = s.post(f'{BASE_URL}/api/login', json={'username': username, 'password': password})
    if resp.status_code != 200:
        print(f"Login failed: {resp.text}")
        return

    # Get Projects
    resp = s.get(f'{BASE_URL}/api/projects')
    if resp.status_code != 200:
        print(f"Get projects failed: {resp.text}")
        return
        
    projects = resp.json()
    print(f"Total projects found: {len(projects)}")
    
    found_6 = False
    for p in projects:
        if str(p.get('id')) == '6':
            print(f"!!! FOUND GHOST PROJECT ID 6 !!!")
            print(json.dumps(p, indent=2, ensure_ascii=False))
            found_6 = True
            
    if not found_6:
        print("Project ID 6 NOT found in list.")

if __name__ == '__main__':
    test_ghost_project('teacher1', 'student123')
