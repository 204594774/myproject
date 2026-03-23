
import sqlite3

def fix_members():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Update the broken leader record (ID 63)
    # Based on previous debug, ID 63 is the leader for Project 17
    print("Fixing project_members for ID 63...")
    cursor.execute('''
        UPDATE project_members 
        SET name = ?, student_id = ? 
        WHERE id = 63
    ''', ('李同学', '202221091347'))
    
    conn.commit()
    conn.close()
    print("Fix complete.")

if __name__ == '__main__':
    fix_members()
