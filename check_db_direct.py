import sqlite3
import os

db_path = r'D:\桌面\new11\database.db'
print(f"Checking DB at: {db_path}")

if not os.path.exists(db_path):
    print("DB file does not exist!")
else:
    try:
        conn = sqlite3.connect(db_path)
        rows = conn.execute("SELECT id, title, status FROM projects").fetchall()
        print(f"Total projects: {len(rows)}")
        for r in rows:
            print(f"ID: {r[0]}, Title: {r[1]}, Status: {r[2]}")
        
        # Check max ID
        max_id = conn.execute("SELECT MAX(id) FROM projects").fetchone()[0]
        print(f"Max ID: {max_id}")
        
        # Check sequence
        seq = conn.execute("SELECT * FROM sqlite_sequence WHERE name='projects'").fetchone()
        print(f"SQLite Sequence for projects: {seq}")

        conn.close()
    except Exception as e:
        print(f"Error: {e}")
