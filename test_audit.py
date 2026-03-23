
import sqlite3
import json
import requests
from app import app, get_db_connection, ROLES

def test_audit_logic():
    # Setup context
    with app.app_context():
        conn = get_db_connection()
        
        # Ensure test user exists
        conn.execute('INSERT OR IGNORE INTO users (username, password, role, real_name) VALUES (?, ?, ?, ?)', 
                    ('test_school', '123', 'school_approver', 'Test School'))
        user_id = conn.execute('SELECT id FROM users WHERE username = ?', ('test_school',)).fetchone()['id']
        
        # Create test project
        conn.execute('INSERT INTO projects (title, status, created_by, project_type, extra_info) VALUES (?, ?, ?, ?, ?)',
                    ('Test Project', 'college_approved', 1, 'innovation', '{}'))
        project_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        conn.commit()
        
        print(f"Created test project {project_id}")
        
        # Test 1: Reject without feedback (Directly calling function logic or mocking request? 
        # Easier to use test client)
        
        client = app.test_client()
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'school_approver'
            
        # 1. Reject no feedback
        res = client.put(f'/api/projects/{project_id}/audit', json={'action': 'reject', 'feedback': ''})
        print(f"Test 1 (No Feedback): Status {res.status_code}, Msg: {res.json}")
        assert res.status_code == 400
        
        # 2. Reject with feedback
        res = client.put(f'/api/projects/{project_id}/audit', json={'action': 'reject', 'feedback': 'Bad quality'})
        print(f"Test 2 (With Feedback): Status {res.status_code}, Msg: {res.json}")
        assert res.status_code == 200
        
        # Verify DB
        project = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
        extra_info = json.loads(project['extra_info'])
        print(f"DB Status: {project['status']}")
        print(f"Extra Info: {extra_info}")
        
        assert project['status'] == 'rejected'
        assert extra_info['rejection_level'] == '学校'
        assert extra_info['rejection_reason'] == 'Bad quality'
        
        # Cleanup
        conn.execute('DELETE FROM projects WHERE id = ?', (project_id,))
        conn.execute('DELETE FROM users WHERE username = ?', ('test_school',))
        conn.commit()
        conn.close()
        print("Test Passed!")

if __name__ == '__main__':
    try:
        test_audit_logic()
    except Exception as e:
        print(f"Test Failed: {e}")
