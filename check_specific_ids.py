import sqlite3
import os

db_path = r'd:\桌面\new11\database.db'

def check_ids():
    if not os.path.exists(db_path):
        print(f"DB not found at {db_path}")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        ids_to_check = [6, 10, 11, 13, 14, 15, 17, 18]
        placeholders = ','.join(['?'] * len(ids_to_check))
        
        print(f"--- Checking Projects {ids_to_check} ---")
        cursor.execute(f"SELECT id, title, created_by, status, project_type FROM projects WHERE id IN ({placeholders})", ids_to_check)
        rows = cursor.fetchall()
        if not rows:
            print("No matching projects found.")
        for row in rows:
            print(f"Found Project: ID={row[0]}, Title='{row[1]}', Creator={row[2]}, Status={row[3]}, Type={row[4]}")
            
        print("\n--- Checking Project Members ---")
        cursor.execute(f"SELECT project_id, student_id, is_leader FROM project_members WHERE project_id IN ({placeholders})", ids_to_check)
        rows = cursor.fetchall()
        if not rows:
            print("No members found for these projects.")
        for row in rows:
            print(f"Member: ProjectID={row[0]}, StudentID={row[1]}, Leader={row[2]}")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    check_ids()
