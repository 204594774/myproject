import requests
import json

BASE_URL = 'http://127.0.0.1:5000'

def test_competitions():
    session = requests.Session()
    
    # Login as student to see competitions
    print("Logging in as student1...")
    session.post(f'{BASE_URL}/api/login', json={'username': 'student1', 'password': 'student123'})
    
    print("Fetching competitions...")
    resp = session.get(f'{BASE_URL}/api/competitions')
    if resp.status_code == 200:
        comps = resp.json()
        print(f"Competitions count: {len(comps)}")
        print(json.dumps(comps, indent=2, ensure_ascii=False))
    else:
        print(f"Error: {resp.status_code} {resp.text}")

if __name__ == '__main__':
    test_competitions()
