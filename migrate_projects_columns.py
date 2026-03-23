import sqlite3
import json

def migrate():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Check existing columns
    cursor.execute("PRAGMA table_info(projects)")
    columns = [r[1] for r in cursor.fetchall()]
    
    # Add competition_id
    if 'competition_id' not in columns:
        print("Adding competition_id column...")
        cursor.execute("ALTER TABLE projects ADD COLUMN competition_id INTEGER")
    else:
        print("competition_id column already exists.")

    # Add extra_info
    if 'extra_info' not in columns:
        print("Adding extra_info column...")
        cursor.execute("ALTER TABLE projects ADD COLUMN extra_info TEXT")
    else:
        print("extra_info column already exists.")

    conn.commit()
    conn.close()

if __name__ == '__main__':
    try:
        migrate()
        print("Migration successful.")
    except Exception as e:
        print(f"Migration failed: {e}")
