import requests
import json
import sqlite3
from werkzeug.security import generate_password_hash

BASE_URL = 'http://127.0.0.1:5000'

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def test_student_competitions():
    # 1. Setup Student User
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM users WHERE username='student_test_comp'")
        conn.commit()
        hashed = generate_password_hash('123456')
        conn.execute("INSERT INTO users (username, password, role, real_name) VALUES ('student_test_comp', ?, 'student', 'Student Test')", (hashed,))
        conn.commit()
    finally:
        conn.close()

    # 2. Login
    session = requests.Session()
    resp = session.post(f'{BASE_URL}/api/login', json={'username': 'student_test_comp', 'password': '123456'})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    print("Login successful")

    # 3. Get Competitions
    resp = session.get(f'{BASE_URL}/api/competitions')
    if resp.status_code != 200:
        print(f"Failed to get competitions: {resp.status_code} {resp.text}")
    else:
        comps = resp.json()
        print(f"Got {len(comps)} competitions")
        for c in comps:
            print(f" - {c['title']} ({c['status']})")

if __name__ == '__main__':
    try:
        test_student_competitions()
    except Exception as e:
        print(f"Test failed: {e}")
