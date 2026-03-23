
import sqlite3
import os

db_path = os.path.join(os.getcwd(), 'instance', 'project_approval.db')
print(f"Checking DB at: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    ids_to_check = [6, 10, 11, 13, 14, 15, 17, 18]
    placeholders = ','.join('?' for _ in ids_to_check)
    query = f"SELECT id, name, status, created_by, project_type FROM projects WHERE id IN ({placeholders})"
    
    cursor.execute(query, ids_to_check)
    rows = cursor.fetchall()
    
    print(f"Found {len(rows)} projects matching IDs {ids_to_check}")
    for row in rows:
        print(f"ID: {row[0]}, Name: {row[1]}, Status: {row[2]}, CreatedBy: {row[3]}, Type: {row[4]}")
        
    # Also check max ID to see where we are
    cursor.execute("SELECT MAX(id) FROM projects")
    max_id = cursor.fetchone()[0]
    print(f"Max ID in DB: {max_id}")

    conn.close()
except Exception as e:
    print(f"Error: {e}")
