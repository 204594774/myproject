import requests
import json

BASE_URL = 'http://127.0.0.1:5000'

def test_detail():
    s = requests.Session()
    # Login as student
    s.post(f'{BASE_URL}/api/login', json={'username': 'student_test_sub', 'password': '123456'})

    
    # Get all projects
    resp = s.get(f'{BASE_URL}/api/projects')
    if resp.status_code != 200:
        print("Failed to get projects")
        return
        
    projects = resp.json()
    if not projects:
        print("No projects found for student")
        return
        
    pid = projects[0]['id']
    print(f"Testing detail for project {pid}...")
    
    resp = s.get(f'{BASE_URL}/api/projects/{pid}')
    if resp.status_code == 200:
        print("Success!")
        print(resp.json())
    else:
        print(f"Failed: {resp.status_code}")
        print(resp.text)

if __name__ == '__main__':
    try:
        test_detail()
    except Exception as e:
        print(f"Error: {e}")
