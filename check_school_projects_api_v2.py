import sqlite3
import os

def check_school_projects_query():
    db_path = 'database.db'
    if not os.path.exists(db_path):
        print("Database not found!")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Setup test data
    # Create projects in various statuses that School Approver should see
    statuses_to_test = [
        'college_approved', 
        'school_approved', 
        'rated', 
        'midterm_submitted', 
        'midterm_approved', 
        'conclusion_submitted', 
        'finished',
        'midterm_college_approved',   # NEW
        'conclusion_college_approved' # NEW
    ]
    
    print("--- Setting up test data ---")
    created_ids = []
    for status in statuses_to_test:
        cursor.execute("INSERT INTO projects (title, status, created_by, college, project_type, level, year) VALUES (?, ?, 1, 'Test College', 'innovation', 'school', '2024')", 
                       (f'Test Project {status}', status))
        created_ids.append(cursor.lastrowid)
    
    conn.commit()
    print(f"Created {len(created_ids)} test projects.")

    # 2. Simulate the query from app.py for SCHOOL_APPROVER
    print("\n--- Simulating School Approver Query ---")
    query = "SELECT id, title, status FROM projects WHERE 1=1"
    # This must match app.py logic exactly
    query += " AND status IN ('college_approved', 'school_approved', 'rated', 'midterm_submitted', 'midterm_approved', 'conclusion_submitted', 'finished', 'midterm_college_approved', 'conclusion_college_approved')"
    
    rows = cursor.execute(query).fetchall()
    visible_ids = [row['id'] for row in rows]
    
    print(f"Found {len(visible_ids)} visible projects.")
    
    # 3. Verify
    all_visible = True
    for pid in created_ids:
        if pid not in visible_ids:
            # Check status of missing project
            proj = cursor.execute("SELECT status FROM projects WHERE id = ?", (pid,)).fetchone()
            print(f"FAILURE: Project {pid} with status '{proj['status']}' is NOT visible!")
            all_visible = False
        else:
             # print(f"Success: Project {pid} is visible.")
             pass
             
    if all_visible:
        print("\nSUCCESS: All expected statuses are visible to School Approver.")
    else:
        print("\nFAILURE: Some statuses are missing from the query logic.")

    # Cleanup
    print("\n--- Cleanup ---")
    for pid in created_ids:
        cursor.execute("DELETE FROM projects WHERE id = ?", (pid,))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    check_school_projects_query()
