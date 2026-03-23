
import sqlite3
import os

db_path = r'd:\桌面\new11\project_management.db'

if not os.path.exists(db_path):
    print(f"File not found: {db_path}")
else:
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        ids_to_check = [6, 10, 11, 13, 14, 15, 17, 18]
        print(f"Checking IDs in {db_path}...")
        
        # Check if projects table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='projects';")
        if not cursor.fetchone():
            print("Table 'projects' does not exist in project_management.db")
        else:
            for pid in ids_to_check:
                try:
                    row = cursor.execute("SELECT id, title, status FROM projects WHERE id = ?", (pid,)).fetchone()
                    if row:
                        print(f"ID {pid}: FOUND - Title: {row[1]}, Status: {row[2]}")
                    else:
                        print(f"ID {pid}: MISSING")
                except Exception as e:
                    print(f"Error querying ID {pid}: {e}")

        conn.close()
    except Exception as e:
        print(f"Connection error: {e}")
