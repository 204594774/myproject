import requests
import json
import sqlite3

BASE_URL = 'http://127.0.0.1:5000'

def login(username, password):
    response = requests.post(f'{BASE_URL}/api/login', json={
        'username': username,
        'password': password
    })
    return response.json(), response.cookies

def get_project_status(project_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.execute('SELECT status FROM projects WHERE id=?', (project_id,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else None

def update_status(project_id, status):
    conn = sqlite3.connect('database.db')
    conn.execute('UPDATE projects SET status=? WHERE id=?', (status, project_id))
    conn.commit()
    conn.close()

# Login as College Approver
username = 'col_approver'
password = 'admin123' 

print(f"Logging in as College Approver: {username}")
user, cookies = login(username, password)
print("Login result:", user)

if 'user' not in user:
    print("Login failed")
    exit(1)

project_id = 17

# 1. Test on Pending status
print("\n--- Testing Edit on Pending Status ---")
update_status(project_id, 'pending')
payload = {
    'title': 'Updated by Approver (Pending)',
    'extra_info': {},
    'members': [] # Simplified
}
response = requests.put(f'{BASE_URL}/api/projects/{project_id}', json=payload, cookies=cookies)
print(f"Status Code: {response.status_code}")
print(f"Response: {response.json()}")

# Verify status didn't change
current_status = get_project_status(project_id)
print(f"Status after edit: {current_status}")
assert current_status == 'pending'

# 2. Test on College Approved status
print("\n--- Testing Edit on College Approved Status ---")
update_status(project_id, 'college_approved')
payload['title'] = 'Updated by Approver (Approved)'
response = requests.put(f'{BASE_URL}/api/projects/{project_id}', json=payload, cookies=cookies)
print(f"Status Code: {response.status_code}")
print(f"Response: {response.json()}")

# Verify status didn't change
current_status = get_project_status(project_id)
print(f"Status after edit: {current_status}")
assert current_status == 'college_approved'

print("\nTest Passed!")
