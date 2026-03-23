import requests
import sqlite3

BASE_URL = 'http://127.0.0.1:5000'

def test_advisor_approved_edit():
    print("--- Setting project 17 to 'advisor_approved' ---")
    conn = sqlite3.connect('database.db')
    conn.execute('UPDATE projects SET status="advisor_approved" WHERE id=17')
    conn.commit()
    conn.close()
    
    # Verify status
    conn = sqlite3.connect('database.db')
    status = conn.execute('SELECT status FROM projects WHERE id=17').fetchone()[0]
    conn.close()
    print(f"Current Status: {status}")
    if status != 'advisor_approved':
        print("Failed to set status!")
        return

    print("\n--- Attempting edit as Student ---")
    # Login
    s = requests.Session()
    resp = s.post(f'{BASE_URL}/api/login', json={'username': 'student1', 'password': 'student123'})
    if resp.status_code != 200:
        print("Login failed")
        return
        
    # Get Project Data
    resp = s.get(f'{BASE_URL}/api/projects/17')
    project_data = resp.json()
    
    # Edit
    print("Sending update request...")
    resp = s.put(f'{BASE_URL}/api/projects/17', json=project_data)
    print(f"Update Response: {resp.status_code} - {resp.text}")
    
    if resp.status_code == 200:
        print("SUCCESS: Edited 'advisor_approved' project.")
        
        # Check if status reverted to pending
        conn = sqlite3.connect('database.db')
        new_status = conn.execute('SELECT status FROM projects WHERE id=17').fetchone()[0]
        conn.close()
        print(f"Post-Edit Status: {new_status}")
    else:
        print("FAIL: Could not edit.")

if __name__ == '__main__':
    test_advisor_approved_edit()
