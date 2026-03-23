
import requests
import json

BASE_URL = 'http://127.0.0.1:5000/api'
SESSION = requests.Session()

def login(username, password):
    print(f"Logging in as {username}...")
    res = SESSION.post(f'{BASE_URL}/login', json={'username': username, 'password': password})
    if res.status_code == 200:
        print("Login successful.")
        return True
    else:
        print(f"Login failed: {res.text}")
        return False

def test_announcement():
    print("\n--- Testing Announcement ---")
    data = {
        'title': 'Test Announcement',
        'content': 'This is a test announcement content.',
        'type': 'notice'
    }
    res = SESSION.post(f'{BASE_URL}/announcements', json=data)
    if res.status_code == 200:
        print("Create announcement: SUCCESS")
    else:
        print(f"Create announcement: FAILED ({res.status_code}) - {res.text}")
        
    # List announcements
    res = SESSION.get(f'{BASE_URL}/announcements')
    if res.status_code == 200:
        items = res.json()
        print(f"Found {len(items)} announcements.")
        # Find our test item
        for item in items:
            if item['title'] == 'Test Announcement':
                print("Verified created announcement in list.")
                # Clean up
                res = SESSION.delete(f"{BASE_URL}/announcements/{item['id']}")
                if res.status_code == 200:
                    print("Delete announcement: SUCCESS")
                else:
                    print(f"Delete announcement: FAILED - {res.text}")
                break
    else:
        print(f"List announcements: FAILED - {res.text}")

def test_competition():
    print("\n--- Testing Competition ---")
    data = {
        'title': 'Test Competition 2025',
        'level': 'National',
        'organizer': 'Ministry of Education',
        'registration_start': '2025-01-01',
        'registration_end': '2025-06-30',
        'description': 'Test Description',
        'status': 'active'
    }
    res = SESSION.post(f'{BASE_URL}/competitions', json=data)
    if res.status_code == 200:
        print("Create competition: SUCCESS")
    else:
        print(f"Create competition: FAILED ({res.status_code}) - {res.text}")
        return

    # List competitions
    res = SESSION.get(f'{BASE_URL}/competitions')
    if res.status_code == 200:
        items = res.json()
        print(f"Found {len(items)} competitions.")
        # Find our test item
        target_id = None
        for item in items:
            if item['title'] == 'Test Competition 2025':
                target_id = item['id']
                print("Verified created competition in list.")
                break
        
        if target_id:
            # Update
            update_data = data.copy()
            update_data['title'] = 'Test Competition 2025 (Updated)'
            res = SESSION.put(f'{BASE_URL}/competitions/{target_id}', json=update_data)
            if res.status_code == 200:
                print("Update competition: SUCCESS")
            else:
                print(f"Update competition: FAILED - {res.text}")
            
            # Delete
            res = SESSION.delete(f'{BASE_URL}/competitions/{target_id}')
            if res.status_code == 200:
                print("Delete competition: SUCCESS")
            else:
                print(f"Delete competition: FAILED - {res.text}")

    else:
        print(f"List competitions: FAILED - {res.text}")

if __name__ == '__main__':
    if login('admin', 'admin123'):
        test_announcement()
        test_competition()
