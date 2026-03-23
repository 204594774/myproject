import requests
import json

BASE_URL = 'http://127.0.0.1:5000/api'
SESSION = requests.Session()

def login(username, password):
    res = SESSION.post(f'{BASE_URL}/login', json={'username': username, 'password': password})
    if res.status_code == 200:
        print(f"Login as {username}: SUCCESS")
        return res.json()['user']
    else:
        print(f"Login as {username}: FAILED - {res.text}")
        return None

def test_flow():
    # 1. Login as student
    user = login('student1', 'student123')
    if not user: return

    # 2. Create Project
    print("\nCreating project...")
    project_data = {
        'title': 'Reproduction Project',
        'project_type': 'innovation',
        'leader_name': user['real_name'],
        'members': [],
        'extra_info': {}
    }
    res = SESSION.post(f'{BASE_URL}/projects', json=project_data)
    if res.status_code == 200:
        pid = res.json()['project_id']
        print(f"Created project ID: {pid}")
    else:
        print(f"Create FAILED: {res.text}")
        return

    # 3. Get Project List
    print("\nFetching projects...")
    res = SESSION.get(f'{BASE_URL}/projects')
    if res.status_code == 200:
        projects = res.json()
        found = False
        for p in projects:
            if p['id'] == pid:
                found = True
                print(f"Found project {pid} in list.")
                break
        if not found:
            print(f"Project {pid} NOT found in list!")
    else:
        print(f"Get projects FAILED: {res.text}")

    # 4. Update Project (Simulate Edit)
    print(f"\nUpdating project {pid}...")
    update_data = project_data.copy()
    update_data['title'] = 'Reproduction Project Updated'
    update_data['id'] = pid # Ensure ID is present in payload if needed (backend doesn't use it from body usually but good to have)
    
    # Frontend sends PUT to /api/projects/{id}
    res = SESSION.put(f'{BASE_URL}/projects/{pid}', json=update_data)
    print(f"Update response code: {res.status_code}")
    print(f"Update response text: {res.text}")

if __name__ == '__main__':
    test_flow()
