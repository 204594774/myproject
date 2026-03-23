import requests
import json

BASE_URL = 'http://127.0.0.1:5000'

def login(username, password):
    print(f"Logging in as {username}...")
    response = requests.post(f'{BASE_URL}/api/login', json={
        'username': username,
        'password': password
    })
    if response.status_code == 200:
        print("Login success")
        return response.cookies
    else:
        print(f"Login failed: {response.text}")
        return None

def debug_view():
    cookies = login('student1', 'student123') # Assuming password is password123 based on previous context
    if not cookies:
        return

    # 1. Get Project List
    print("\n--- Fetching Project List ---")
    resp = requests.get(f'{BASE_URL}/api/projects', cookies=cookies)
    if resp.status_code == 200:
        projects = resp.json()
        target_project = next((p for p in projects if p['id'] == 17), None)
        if target_project:
            print(f"Project 17 found in list:")
            print(f"  Status: {target_project.get('status')}")
            print(f"  Title: {target_project.get('title')}")
            print(f"  Leader: {target_project.get('leader_name')}")
        else:
            print("Project 17 NOT found in list!")
    else:
        print(f"Failed to fetch list: {resp.status_code}")

    # 2. Get Project Detail
    print("\n--- Fetching Project Detail (ID=17) ---")
    resp = requests.get(f'{BASE_URL}/api/projects/17', cookies=cookies)
    if resp.status_code == 200:
        project = resp.json()
        print(f"Project 17 Detail:")
        print(f"  Status: {project.get('status')}")
        print(f"  Created By: {project.get('created_by')}")
        print(f"  Leader ID (in extra_info): {project.get('extra_info', {}).get('leader_info', {}).get('id')}")
    else:
        print(f"Failed to fetch detail: {resp.status_code} - {resp.text}")

if __name__ == '__main__':
    debug_view()
