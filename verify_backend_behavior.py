import requests
import json

BASE_URL = 'http://127.0.0.1:5000'

def test_duplicate_creation():
    session = requests.Session()
    
    # 1. Login
    print("Logging in...")
    resp = session.post(f'{BASE_URL}/api/login', json={
        'username': 'student1',
        'password': 'student123'
    })
    if resp.status_code != 200:
        print("Login failed")
        return
    print("Login successful")

    # 2. Create Project A
    print("Creating Project A...")
    project_data = {
        'title': 'Test Project A',
        'project_type': 'innovation',
        'members': []
    }
    resp = session.post(f'{BASE_URL}/api/projects', json=project_data)
    if resp.status_code != 200:
        print(f"Create failed: {resp.text}")
        return
    
    project_id = resp.json().get('project_id')
    print(f"Project A created with ID: {project_id}")

    # 3. Simulate frontend bug: Sending POST with existing ID
    print("Simulating frontend bug (POST with existing ID)...")
    duplicate_payload = project_data.copy()
    duplicate_payload['id'] = project_id # Including the ID
    duplicate_payload['title'] = 'Test Project A - Duplicate Attempt'

    resp = session.post(f'{BASE_URL}/api/projects', json=duplicate_payload)
    
    if resp.status_code == 200:
        new_id = resp.json().get('project_id')
        print(f"Server responded with 200. New ID: {new_id}")
        if new_id != project_id:
            print("CONFIRMED: Backend creates new project even if ID is provided in POST.")
            print("This validates that the frontend fix (forcing PUT) is necessary.")
        else:
            print("Surprise: Backend returned same ID?")
    else:
        print(f"Server error: {resp.status_code} {resp.text}")

if __name__ == '__main__':
    test_duplicate_creation()
