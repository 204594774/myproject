
import requests
import json

BASE_URL = 'http://127.0.0.1:5000'

def login(username, password):
    s = requests.Session()
    resp = s.post(f'{BASE_URL}/api/login', json={'username': username, 'password': password})
    if resp.status_code != 200:
        print(f"Login failed for {username}: {resp.text}")
        return None
    return s

def test_system_admin():
    print("\n--- Testing System Admin ---")
    s = login('admin', 'admin123') # Assuming admin/admin123 (need to verify password)
    if not s: 
        # Try default password 'admin' if admin123 fails? 
        # From previous context app.js: admin / admin123
        return

    # 1. List Users
    resp = s.get(f'{BASE_URL}/api/users')
    print(f"List Users: {resp.status_code} (Expected: 200)")
    users = resp.json()
    print(f"Total Users: {len(users)}")
    
    # 2. Create User
    new_user = {
        'username': 'test_pa', 'password': '123', 'role': 'project_admin', 'real_name': 'Test PA'
    }
    resp = s.post(f'{BASE_URL}/api/users', json=new_user)
    print(f"Create Project Admin: {resp.status_code} (Expected: 200/400)")
    
    # 3. Update User (student1)
    resp = s.put(f'{BASE_URL}/api/users/7', json={'real_name': '李同学(Modified)'})
    print(f"Update student1: {resp.status_code} (Expected: 200)")
    
    # 4. Delete User (test_pa)
    # Find ID of test_pa
    users = s.get(f'{BASE_URL}/api/users').json()
    target = next((u for u in users if u['username'] == 'test_pa'), None)
    if target:
        resp = s.delete(f'{BASE_URL}/api/users/{target["id"]}')
        print(f"Delete test_pa: {resp.status_code} (Expected: 200)")

def test_project_admin():
    print("\n--- Testing Project Admin ---")
    s = login('proj_admin', 'admin123') # Assuming password is same as admin or needs reset?
    # I'll try admin123. If fail, I might need to reset it using admin first.
    if not s: return

    # 1. List Users (Should filter)
    resp = s.get(f'{BASE_URL}/api/users')
    print(f"List Users: {resp.status_code}")
    users = resp.json()
    roles = set(u['role'] for u in users)
    print(f"Visible Roles: {roles} (Expected: {{'student', 'teacher'}})")
    
    # 2. Update Student (student1)
    resp = s.put(f'{BASE_URL}/api/users/7', json={'real_name': '李同学(PA)'})
    print(f"Update student1: {resp.status_code} (Expected: 200)")
    
    # 3. Update Admin (admin - ID 1) -> Should Fail
    resp = s.put(f'{BASE_URL}/api/users/1', json={'real_name': 'Hacked'})
    print(f"Update admin: {resp.status_code} (Expected: 403)")
    
    # 4. Create Student
    new_stu = {'username': 'test_stu_pa', 'password': '123', 'role': 'student', 'real_name': 'Test Stu PA'}
    resp = s.post(f'{BASE_URL}/api/users', json=new_stu)
    print(f"Create Student: {resp.status_code} (Expected: 200)")
    
    # 5. Create Judge -> Should Fail
    new_judge = {'username': 'test_judge_pa', 'password': '123', 'role': 'judge', 'real_name': 'Test Judge PA'}
    resp = s.post(f'{BASE_URL}/api/users', json=new_judge)
    print(f"Create Judge: {resp.status_code} (Expected: 403)")
    
    # Cleanup
    users = s.get(f'{BASE_URL}/api/users').json()
    target = next((u for u in users if u['username'] == 'test_stu_pa'), None)
    if target:
        s.delete(f'{BASE_URL}/api/users/{target["id"]}')

if __name__ == '__main__':
    test_system_admin()
    test_project_admin()
