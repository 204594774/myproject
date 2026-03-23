import requests
import json

BASE_URL = 'http://127.0.0.1:5000'

def login(username, password):
    response = requests.post(f'{BASE_URL}/api/login', json={
        'username': username,
        'password': password
    })
    return response.json(), response.cookies

# Login as Student
username = 'student1'
password = 'student123' 

print(f"Logging in as Student: {username}")
user, cookies = login(username, password)
print("Login result:", user)

if 'user' not in user:
    print("Login failed")
    exit(1)

project_id = 17

# Prepare update data (mimicking what frontend sends)
# We need to fetch the project first to get existing data, but for this test we'll construct a minimal valid payload
# based on what update_project expects.

payload = {
    'title': 'Updated Title',
    'leader_name': '李同学',
    'advisor_name': '张老师',
    'department': '软件工程',
    'college': '计算机学院（人工智能学院）',
    'project_type': 'entrepreneurship_training',
    'level': 'undergrad',
    'year': '2025',
    'abstract': 'Updated Abstract',
    'assessment_indicators': 'Updated Indicators',
    'extra_info': {
        'leader_info': {'name': '李同学', 'id': '202221091347'},
        'advisor_info': {'dept': '计算机学院'}
    },
    'members': []
}

print(f"Attempting to update Project {project_id}...")
response = requests.put(f'{BASE_URL}/api/projects/{project_id}', json=payload, cookies=cookies)

print(f"Status Code: {response.status_code}")
print(f"Response: {response.json()}")
