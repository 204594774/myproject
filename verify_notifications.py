import requests
import sqlite3
from werkzeug.security import generate_password_hash

BASE_URL = 'http://127.0.0.1:5000'
COLLEGE_NAME = 'Notification Test College'

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def setup_users():
    conn = get_db_connection()
    pwd = generate_password_hash('123456')
    
    # 1. Student
    conn.execute("DELETE FROM users WHERE username IN ('stu_notif', 'tea_notif', 'col_notif')")
    conn.execute("INSERT INTO users (username, password, role, real_name, college, department, identity_number) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ('stu_notif', pwd, 'student', 'Stu Notif', COLLEGE_NAME, 'Dept A', 'S001'))
    
    # 2. Teacher
    conn.execute("INSERT INTO users (username, password, role, real_name, college) VALUES (?, ?, ?, ?, ?)",
                ('tea_notif', pwd, 'teacher', 'Tea Notif', COLLEGE_NAME))
                
    # 3. College Admin
    conn.execute("INSERT INTO users (username, password, role, real_name, college) VALUES (?, ?, ?, ?, ?)",
                ('col_notif', pwd, 'college_approver', 'Col Notif', COLLEGE_NAME))
                
    conn.commit()
    conn.close()

def test_flow():
    session = requests.Session()
    
    # 1. Login as Student
    resp = session.post(f'{BASE_URL}/api/login', json={'username': 'stu_notif', 'password': '123456'})
    assert resp.status_code == 200, "Student login failed"
    
    # 2. Submit Project
    payload = {
        'title': 'Notification Test Project',
        'project_type': 'innovation',
        'advisor_name': 'Tea Notif', # Matches real_name of teacher
        'college': COLLEGE_NAME,
        'members': [],
        'extra_info': {}
    }
    resp = session.post(f'{BASE_URL}/api/projects', json=payload)
    assert resp.status_code == 200, f"Submission failed: {resp.text}"
    project_id = resp.json()['project_id']
    print(f"Project submitted with ID: {project_id}")
    
    # 3. Check Teacher Visibility & Notification
    s_tea = requests.Session()
    s_tea.post(f'{BASE_URL}/api/login', json={'username': 'tea_notif', 'password': '123456'})
    
    # Check Projects
    resp = s_tea.get(f'{BASE_URL}/api/projects')
    projects = resp.json()
    found = any(p['id'] == project_id for p in projects)
    print(f"Teacher sees project: {found}")
    
    # Check Notifications (Need to access DB directly as API might not expose all logic easily or I'd have to mock)
    # Actually, let's just check DB for notifications to be sure
    conn = get_db_connection()
    tea_id = conn.execute("SELECT id FROM users WHERE username='tea_notif'").fetchone()[0]
    notifs = conn.execute("SELECT * FROM notifications WHERE user_id=?", (tea_id,)).fetchall()
    print(f"Teacher notifications: {len(notifs)}")
    if len(notifs) > 0:
        print(f"  - {notifs[0]['content']}")
        
    # 4. Check College Admin Visibility & Notification
    s_col = requests.Session()
    s_col.post(f'{BASE_URL}/api/login', json={'username': 'col_notif', 'password': '123456'})
    
    # Check Projects
    resp = s_col.get(f'{BASE_URL}/api/projects')
    projects = resp.json()
    found_col = any(p['id'] == project_id for p in projects)
    print(f"College Admin sees project: {found_col}")
    
    col_id = conn.execute("SELECT id FROM users WHERE username='col_notif'").fetchone()[0]
    notifs_col = conn.execute("SELECT * FROM notifications WHERE user_id=?", (col_id,)).fetchall()
    print(f"College Admin notifications: {len(notifs_col)}")
    if len(notifs_col) > 0:
        print(f"  - {notifs_col[0]['content']}")

    conn.close()

if __name__ == '__main__':
    try:
        setup_users()
        test_flow()
    except Exception as e:
        print(f"Test failed: {e}")
