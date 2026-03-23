import sqlite3

def check_school_projects_api():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    
    # Simulate School Approver logic
    role = 'school_approver'
    
    query = "SELECT id, title, status FROM projects WHERE 1=1"
    
    # Logic from app.py
    query += " AND status IN ('college_approved', 'school_approved', 'rated', 'midterm_submitted', 'midterm_approved', 'conclusion_submitted', 'finished')"
    query += " ORDER BY created_at DESC"
    
    print(f"Executing query: {query}")
    
    projects = conn.execute(query).fetchall()
    
    print(f"Found {len(projects)} projects visible to School Approver:")
    for p in projects:
        print(f"  [{p['id']}] {p['title']} (Status: {p['status']})")
        
    # Also check what projects exist but are hidden
    all_projects = conn.execute("SELECT id, title, status FROM projects").fetchall()
    print(f"\nAll Projects in DB ({len(all_projects)}):")
    for p in all_projects:
        visible = any(vp['id'] == p['id'] for vp in projects)
        if not visible:
            print(f"  [HIDDEN] [{p['id']}] {p['title']} (Status: {p['status']})")
        else:
            print(f"  [VISIBLE] [{p['id']}] {p['title']} (Status: {p['status']})")

    conn.close()

if __name__ == "__main__":
    check_school_projects_api()
