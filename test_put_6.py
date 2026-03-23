import requests
import json

def test_put_6():
    session = requests.Session()
    # Login first
    login_url = 'http://127.0.0.1:5000/api/login'
    login_data = {'username': 'student1', 'password': 'student123'} 
    
    print("Attempting login as student1...")
    try:
        r = session.post(login_url, json=login_data)
        if r.status_code != 200:
            print(f"Login failed: {r.text}")
            return
        print("Login successful")
        
        # Now try PUT 6
        url = 'http://127.0.0.1:5000/api/projects/6'
        headers = {'Content-Type': 'application/json'}
        data = {'title': 'Test Project 6'}
        
        print(f"Sending PUT to {url}...")
        response = session.put(url, json=data, headers=headers)
        print(f"PUT Status Code: {response.status_code}")
        print(f"PUT Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    test_put_6()
