import requests
import json
import sqlite3
from werkzeug.security import generate_password_hash

BASE_URL = 'http://127.0.0.1:5000'

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def test_student_submission():
    # 1. Setup Student User
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM users WHERE username='student_test_sub'")
        conn.commit()
        hashed = generate_password_hash('123456')
        # Ensure user has college/department for full testing, though code handles NULLs now
        conn.execute('''
            INSERT INTO users (username, password, role, real_name, college, department, identity_number) 
            VALUES ('student_test_sub', ?, 'student', 'Student Sub Test', 'Test College', 'Test Dept', 'S12345')
        ''', (hashed,))
        conn.commit()
        
        # Ensure at least one competition exists
        comps = conn.execute("SELECT id FROM competitions WHERE status='active'").fetchall()
        if not comps:
            print("No active competitions found, creating one...")
            conn.execute("INSERT INTO competitions (title, status) VALUES ('Test Comp', 'active')")
            conn.commit()
            comp_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        else:
            comp_id = comps[0]['id']
            
    finally:
        conn.close()

    # 2. Login
    session = requests.Session()
    resp = session.post(f'{BASE_URL}/api/login', json={'username': 'student_test_sub', 'password': '123456'})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    print("Login successful")

    # 3. Submit Project (Innovation)
    payload_innov = {
        'title': 'Test Project Innovation',
        'project_type': 'innovation',
        'competition_id': comp_id,
        'members': [],
        'leader_name': 'Student Sub Test',
        'major': 'CS',
        'extra_info': {},
        'risk_control': 'Risk Control'
    }
    
    resp = session.post(f'{BASE_URL}/api/projects', json=payload_innov)
    if resp.status_code == 200:
        print("Innovation Project submitted successfully!")
    else:
        print(f"Innovation Submission failed: {resp.status_code}")
        print(resp.text)

    # 4. Submit Project (Entrepreneurship)
    payload_ent = {
        'title': 'Test Project Entrepreneurship',
        'project_type': 'entrepreneurship',
        'competition_id': comp_id,
        'members': [],
        'leader_name': 'Student Sub Test',
        'major': 'CS',
        'extra_info': {},
        'team_intro': 'Team Intro',
        'market_prospect': 'Market',
        'operation_mode': 'Mode',
        'financial_budget': 'Budget',
        'risk_budget': 'Risk',
        'investment_budget': 'Invest',
        'source': 'Source',
        'tech_maturity': 'Tech',
        'enterprise_mentor': 'Mentor',
        'innovation_content': 'Content'
    }

    resp = session.post(f'{BASE_URL}/api/projects', json=payload_ent)
    if resp.status_code == 200:
        print("Entrepreneurship Project submitted successfully!")
    else:
        print(f"Entrepreneurship Submission failed: {resp.status_code}")
        print(resp.text)

if __name__ == '__main__':
    try:
        test_student_submission()
    except Exception as e:
        print(f"Test failed: {e}")
