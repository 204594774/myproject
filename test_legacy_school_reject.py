import json
from app import app, get_db_connection, ROLES

def setup_project_with_school_stage():
    conn = get_db_connection()
    conn.execute("INSERT OR IGNORE INTO users (username, password, role, real_name) VALUES (?, ?, ?, ?)",
                 ('legacy_school', '123', ROLES['SCHOOL_APPROVER'], 'Legacy School'))
    school_id = conn.execute("SELECT id FROM users WHERE username = ?", ('legacy_school',)).fetchone()['id']
    conn.execute("INSERT INTO projects (title, status, created_by, project_type, extra_info) VALUES (?, ?, ?, ?, ?)",
                 ('Legacy Actions Project', 'college_approved', 1, 'innovation', '{}'))
    project_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    conn.commit()
    conn.close()
    return school_id, project_id

def test_project_reject_with_legacy_action():
    school_id, project_id = setup_project_with_school_stage()
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = school_id
        sess['role'] = ROLES['SCHOOL_APPROVER']
    # legacy action value 'rejected' (old frontend)
    res = client.put(f'/api/projects/{project_id}/audit', json={'action': 'rejected', 'feedback': ''})
    print('Project reject legacy action, empty feedback:', res.status_code, res.json)
    assert res.status_code == 400

def setup_file_with_school_stage():
    conn = get_db_connection()
    pid = conn.execute("SELECT id FROM projects WHERE title = ?", ('Legacy Actions Project',)).fetchone()['id']
    conn.execute("INSERT INTO project_files (project_id, file_type, file_path, original_filename, status) VALUES (?, ?, ?, ?, ?)",
                 (pid, 'midterm', '/uploads/legacy', 'midterm.pdf', 'pending'))
    conn.execute("UPDATE projects SET status = 'midterm_college_approved' WHERE id = ?", (pid,))
    conn.commit()
    conn.close()
    return pid

def test_file_reject_with_legacy_action():
    conn = get_db_connection()
    school_id = conn.execute("SELECT id FROM users WHERE username = ?", ('legacy_school',)).fetchone()['id']
    conn.close()
    pid = setup_file_with_school_stage()
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = school_id
        sess['role'] = ROLES['SCHOOL_APPROVER']
    # legacy action value 'rejected' (old frontend)
    res = client.put(f'/api/projects/{pid}/files/audit', json={'file_type': 'midterm', 'action': 'rejected', 'feedback': ''})
    print('File reject legacy action, empty feedback:', res.status_code, res.json)
    assert res.status_code == 400

if __name__ == '__main__':
    test_project_reject_with_legacy_action()
    test_file_reject_with_legacy_action()
    print('Legacy school reject tests passed')
