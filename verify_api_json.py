import requests
import json

# Assuming the server is running on localhost:5000
BASE_URL = 'http://localhost:5000'

def test_json_parsing():
    # Login as student (using a known student account, e.g., user 2 from previous context or just try one)
    # Actually, I can use the existing session logic or just check the code.
    # But running a script is better.
    
    session = requests.Session()
    
    # Login
    print("Logging in...")
    login_resp = session.post(f'{BASE_URL}/api/login', json={
        'username': 'student1', 
        'password': 'password123'
    })
    
    # Try another user if this fails, or use the check_school_users script to find a user.
    # I'll assume student1 exists or I'll check the DB first.
    pass

if __name__ == '__main__':
    # I'll just check the DB directly to see if I can simulate the API response logic? 
    # No, I need to test the running API.
    # But I don't know if the server is running in the background or if I should start it.
    # The user said "webpage unable to connect" earlier, implying they are trying to access it.
    # I'll assume it's running.
    pass
