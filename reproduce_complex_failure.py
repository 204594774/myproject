import requests
import json
import time

BASE_URL = 'http://127.0.0.1:5000'
SESSION = requests.Session()

def login(username, password):
    resp = SESSION.post(f'{BASE_URL}/api/login', json={
        'username': username,
        'password': password
    })
    if resp.status_code != 200:
        print(f"Login failed: {resp.text}")
        return False
    print(f"Login successful as {username}")
    return True

def test_update_full_payload(project_id):
    print(f"\n--- Testing Update for Project ID {project_id} ---")
    
    # 1. Simulate editProject: GET project details
    print(f"GET /api/projects/{project_id}")
    resp = SESSION.get(f'{BASE_URL}/api/projects/{project_id}')
    if resp.status_code == 404:
        print(f"FAILURE: Project {project_id} not found (404) during fetch.")
        return
    
    project = resp.json()
    print(f"Project fetched. Title: {project.get('title')}")
    
    # 2. Simulate app.js createForm construction
    # Note: app.js parses extra_info deep copy
    extra_info = project.get('extra_info', {})
    # If it comes as string (it shouldn't from API, but let's check), parse it
    if isinstance(extra_info, str):
        extra_info = json.loads(extra_info)
        
    createForm = {
        'id': project.get('id'),
        'status': project.get('status'),
        'title': project.get('title'),
        'project_type': project.get('project_type'),
        'level': project.get('level'),
        'year': project.get('year'),
        'leader_name': project.get('leader_name'),
        'advisor_name': project.get('advisor_name'),
        'department': project.get('department'),
        'college': project.get('college'),
        'abstract': project.get('abstract'),
        'assessment_indicators': project.get('assessment_indicators'),
        'competition_id': project.get('competition_id'),
        'template_type': project.get('template_type', 'default'),
        'extra_info': extra_info,
        # Extended fields
        'background': project.get('background'),
        'content': project.get('content'),
        'members': project.get('members', [])
    }
    
    # 3. Simulate user modification
    new_title = f"{project.get('title')} - ComplexUpdate_{int(time.time())}"
    createForm['title'] = new_title
    
    # Simulate modifying extra_info
    if 'extra_info' not in createForm or not isinstance(createForm['extra_info'], dict):
        createForm['extra_info'] = {}
    createForm['extra_info']['progress'] = f"UpdateTest_{int(time.time())}"
    
    # Simulate adding a member (often causes issues if structure is wrong)
    if not createForm.get('members'):
        createForm['members'] = []
    # app.js might filter members. usually removes leader if stored separately.
    
    # 4. Simulate submitProject payload preparation
    payload = json.loads(json.dumps(createForm)) # Deep copy
    
    # 5. Send PUT
    print(f"PUT /api/projects/{project_id} with new title: {new_title}")
    resp = SESSION.put(f'{BASE_URL}/api/projects/{project_id}', json=payload)
    
    if resp.status_code == 200:
        print("PUT successful.")
        # 6. Verify persistence
        resp2 = SESSION.get(f'{BASE_URL}/api/projects/{project_id}')
        p2 = resp2.json()
        if p2.get('title') == new_title:
            print("SUCCESS: Title updated and persisted.")
        else:
            print(f"FAILURE: Title NOT updated. Got: {p2.get('title')}")
    elif resp.status_code == 404:
        print("FAILURE: Got 404 Not Found during PUT.")
        try:
            print(f"Response: {resp.json()}")
        except:
            print(f"Response text: {resp.text}")
    else:
        print(f"FAILURE: Status {resp.status_code}")
        print(resp.text)

if __name__ == '__main__':
    if login('student1', 'student123'):
        # Test problematic IDs
        test_update_full_payload(18)
        test_update_full_payload(15)
        test_update_full_payload(11)
        test_update_full_payload(10)
        test_update_full_payload(13)
