import sqlite3
import os

# Use the absolute path provided in the environment or by previous context
db_path = r"d:\桌面\new11\instance\project_management.db"
# Fallback or alternative path if the above doesn't exist (based on database.py)
# database.py uses d:\桌面\new11\database.db, let's check that one too.
db_path_alt = r"d:\桌面\new11\database.db"

def check_db(path):
    print(f"Checking DB: {path}")
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return

    try:
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check projects table
        print("--- Projects with ID 6 ---")
        rows = cursor.execute("SELECT * FROM projects WHERE id = 6").fetchall()
        if not rows:
            print("No project with ID 6 found.")
        else:
            for r in rows:
                print(dict(r))

        # Check notifications table
        print("--- Notifications referencing ID 6 ---")
        try:
            # Check for notifications that might contain "ID: 6" or similar
            rows = cursor.execute("SELECT * FROM notifications WHERE content LIKE '%ID: 6%' OR content LIKE '%项目：6%' OR content LIKE '%项目ID 6%'").fetchall()
            if not rows:
                print("No notifications explicitly referencing ID 6 found.")
            else:
                for r in rows:
                    print(dict(r))
            
            # Dump all notifications just in case
            print("--- All Notifications (First 10) ---")
            rows = cursor.execute("SELECT * FROM notifications LIMIT 10").fetchall()
            for r in rows:
                print(dict(r))
        except Exception as e:
            print(f"Error checking notifications: {e}")

        # Check competitions table (It defines competitions, doesn't link to projects usually, 
        # but let's check if there's any odd column if schema allowed, but we know schema now)
        # Schema: id, title, level, ... form_config, template_type. No project_id.
        # So we skip checking competitions table for project_id.
        print("--- Competitions check skipped (no project_id column) ---")

        # Check for max ID
        print("--- Max ID ---")
        row = cursor.execute("SELECT MAX(id) as max_id FROM projects").fetchone()
        print(f"Max ID: {row['max_id']}")

        # List all IDs
        print("--- All Project IDs ---")
        rows = cursor.execute("SELECT id FROM projects").fetchall()
        ids = [r['id'] for r in rows]
        print(ids)

        conn.close()
    except Exception as e:
        print(f"Error reading {path}: {e}")

# Updated path to match database.py
db_path = r'D:\桌面\new11\database.db'
check_db(db_path)
