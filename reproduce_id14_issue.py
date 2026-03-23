import requests
import json
import sys

BASE_URL = 'http://127.0.0.1:5000'

def login(username, password):
    session = requests.Session()
    resp = session.post(f'{BASE_URL}/api/login', json={'username': username, 'password': password})
    if resp.status_code != 200:
        print(f"Login failed: {resp.text}")
        sys.exit(1)
    print(f"Login successful as {username}")
    return session

def test_update_project_14():
    session = login('student1', 'student123')
    
    # 1. Get initial project count
    resp = session.get(f'{BASE_URL}/api/projects')
    projects_before = resp.json()
    count_before = len(projects_before)
    print(f"Initial project count: {count_before}")
    
    # Check if ID 14 exists
    p14 = next((p for p in projects_before if p['id'] == 14), None)
    if not p14:
        print("Project ID 14 not found!")
        # Try to find any project to test
        if projects_before:
            p14 = projects_before[0]
            print(f"Testing with project ID {p14['id']} instead.")
        else:
            print("No projects found to test.")
            return

    print(f"Testing update on Project ID: {p14['id']}")
    
    # 2. Update Project 14 (PUT)
    update_payload = {
        "title": f"{p14['title']} - Updated",
        "project_type": p14['project_type'],
        "id": p14['id'], # Frontend sends ID in body too
        "members": [],
        "extra_info": {}
    }
    
    print("Sending PUT request...")
    resp = session.put(f'{BASE_URL}/api/projects/{p14["id"]}', json=update_payload)
    print(f"PUT Response Code: {resp.status_code}")
    print(f"PUT Response Body: {resp.text}")
    
    # 3. Check for duplicates
    resp = session.get(f'{BASE_URL}/api/projects')
    projects_after = resp.json()
    count_after = len(projects_after)
    print(f"Final project count: {count_after}")
    
    if count_after > count_before:
        print("FAIL: Project count increased! Duplicate created.")
        new_projects = [p for p in projects_after if p['id'] not in [op['id'] for op in projects_before]]
        print(f"New projects: {new_projects}")
    else:
        print("PASS: Project count remained same.")

    # 4. Simulate the bug: sending POST with ID (which shouldn't happen with frontend fix, but checking backend behavior)
    # Actually, the user says "still happens", implying the frontend might still be doing something wrong OR backend treats something wrong.
    # But let's verify if my previous backend test was correct.
    
if __name__ == '__main__':
    test_update_project_14()
