import sqlite3
import json

def fix_data():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Update User 7 (student1) identity_number
    user_id = 7
    new_id_number = '202221091347'
    print(f"Updating user {user_id} identity_number to {new_id_number}...")
    cursor.execute('UPDATE users SET identity_number = ? WHERE id = ?', (new_id_number, user_id))
    
    # Verify User Update
    user = cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    print(f"User {user_id} updated: identity_number={user['identity_number']}")

    # 2. Update Project 17 Leader in project_members
    project_id = 17
    print(f"Updating project {project_id} leader info in project_members...")
    
    # Find the leader record
    leader_member = cursor.execute('SELECT * FROM project_members WHERE project_id = ? AND is_leader = 1', (project_id,)).fetchone()
    
    if leader_member:
        member_id = leader_member['id']
        cursor.execute('''
            UPDATE project_members 
            SET student_id = ?, name = ? 
            WHERE id = ?
        ''', (new_id_number, '李同学', member_id))
        print(f"Project member {member_id} updated.")
    else:
        print("Leader member not found, creating one...")
        cursor.execute('''
            INSERT INTO project_members (project_id, is_leader, name, student_id)
            VALUES (?, 1, ?, ?)
        ''', (project_id, '李同学', new_id_number))

    conn.commit()
    conn.close()
    print("Data fix completed.")

if __name__ == '__main__':
    fix_data()
