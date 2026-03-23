import sqlite3
import json

def check_projects():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    
    print("--- All Projects ---")
    projects = conn.execute('SELECT id, title, created_by FROM projects').fetchall()
    for p in projects:
        print(f"ID: {p['id']}, Title: {p['title']}, Created By: {p['created_by']}")
    
    print("--- Projects 4 and 5 ---")
    projects = conn.execute('SELECT * FROM projects WHERE id IN (4, 5)').fetchall()
    for p in projects:
        print(f"ID: {p['id']}, Title: {p['title']}, Created By: {p['created_by']}, Created At: {p['created_at']}")
        print(f"  Type: {p['project_type']}, Status: {p['status']}")
        
        # Check specific tables
        if p['project_type'] == 'innovation':
            extra = conn.execute('SELECT * FROM innovation_projects WHERE project_id = ?', (p['id'],)).fetchone()
            print(f"  Innovation Data: {dict(extra) if extra else 'None'}")
        else:
            extra = conn.execute('SELECT * FROM entrepreneurship_projects WHERE project_id = ?', (p['id'],)).fetchone()
            print(f"  Entrepreneurship Data: {dict(extra) if extra else 'None'}")
            
    conn.close()

if __name__ == '__main__':
    check_projects()
