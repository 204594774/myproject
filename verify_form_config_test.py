import requests
import json
import sqlite3
from werkzeug.security import generate_password_hash

BASE_URL = 'http://127.0.0.1:5000'

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def test_form_config():
    # 1. Login as admin
    session = requests.Session()
    # Assuming we have a way to login or we can just insert a user directly into DB if needed, 
    # but let's try to use the API if possible.
    # We need a system admin. Let's check if one exists or create one.
    
    conn = get_db_connection()
    try:
        # Ensure fresh user
        conn.execute("DELETE FROM users WHERE username='admin_test_config'")
        conn.commit()
        hashed = generate_password_hash('123456')
        conn.execute("INSERT INTO users (username, password, role, real_name) VALUES ('admin_test_config', ?, 'system_admin', 'Admin Test')", (hashed,))
        conn.commit()
    finally:
        conn.close()

    resp = session.post(f'{BASE_URL}/api/login', json={'username': 'admin_test_config', 'password': '123456'})
    assert resp.status_code == 200, f"Login failed: {resp.text}"

    # 2. Create competition with custom form_config
    config = {
        'show_company_info': False,
        'show_advisor': True,
        'show_team_members': False, # Hide team members
        'show_attachments': True
    }
    
    comp_data = {
        'title': 'Config Test Competition',
        'level': 'School',
        'organizer': 'Test Org',
        'registration_start': '2025-01-01',
        'registration_end': '2025-12-31',
        'description': 'Test Description',
        'form_config': config
    }
    
    resp = session.post(f'{BASE_URL}/api/competitions', json=comp_data)
    assert resp.status_code == 200, f"Create competition failed: {resp.text}"
    print("Competition created successfully.")

    # 3. Fetch competitions and verify config
    resp = session.get(f'{BASE_URL}/api/competitions')
    assert resp.status_code == 200
    comps = resp.json()
    
    target_comp = None
    for c in comps:
        if c['title'] == 'Config Test Competition':
            target_comp = c
            break
            
    assert target_comp is not None, "Competition not found"
    
    # Verify form_config comes back as string (since it's TEXT in DB) or JSON if API parsed it?
    # In app.py get_competitions: return jsonify([dict(row) ...])
    # SQLite returns TEXT columns as strings.
    
    returned_config_str = target_comp.get('form_config')
    print(f"Returned config: {returned_config_str} (type: {type(returned_config_str)})")
    
    if returned_config_str:
        returned_config = json.loads(returned_config_str)
        assert returned_config['show_team_members'] is False
        assert returned_config['show_advisor'] is True
        print("Config verification passed: Team members hidden, Advisor shown.")
    else:
        print("Error: form_config is None/Empty")
        exit(1)

if __name__ == '__main__':
    try:
        test_form_config()
    except Exception as e:
        print(f"Test failed: {e}")
        exit(1)
