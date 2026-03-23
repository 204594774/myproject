
from app import app, get_db_connection
import sqlite3

def check_ids():
    with app.app_context():
        try:
            conn = get_db_connection()
            # IDs reported by user as problematic
            ids_to_check = [6, 10, 11, 13, 14, 15, 17, 18]
            placeholders = ','.join('?' for _ in ids_to_check)
            
            print(f"\n--- Checking Projects {ids_to_check} ---")
            query = f"SELECT id, title, status, created_by, project_type FROM projects WHERE id IN ({placeholders})"
            rows = conn.execute(query, ids_to_check).fetchall()
            
            found_ids = [row['id'] for row in rows]
            print(f"Found {len(rows)} projects.")
            for row in rows:
                print(f"[FOUND] ID: {row['id']} | Title: {row['title']} | Status: {row['status']} | CreatedBy: {row['created_by']} | Type: {row['project_type']}")
            
            missing_ids = [id for id in ids_to_check if id not in found_ids]
            if missing_ids:
                print(f"[MISSING] The following IDs were NOT found in DB: {missing_ids}")
            
            # List ALL IDs
            print(f"\n--- Listing ALL Project IDs ---")
            all_rows = conn.execute("SELECT id, title FROM projects ORDER BY id").fetchall()
            print(f"Total projects: {len(all_rows)}")
            for row in all_rows:
                 print(f"ID: {row['id']} | Title: {row['title']}")
            
            conn.close()
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    check_ids()
