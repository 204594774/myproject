import sqlite3
import json

def migrate():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Check existing columns
    cursor.execute("PRAGMA table_info(users)")
    columns = [r[1] for r in cursor.fetchall()]
    print(f"Current columns: {columns}")
    
    # Add department
    if 'department' not in columns:
        print("Adding department column...")
        cursor.execute("ALTER TABLE users ADD COLUMN department TEXT")
    else:
        print("department column already exists.")

    # Add college
    if 'college' not in columns:
        print("Adding college column...")
        cursor.execute("ALTER TABLE users ADD COLUMN college TEXT")
    else:
        print("college column already exists.")
        
    # Add status
    if 'status' not in columns:
        print("Adding status column...")
        cursor.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'active'")
    else:
        print("status column already exists.")

    conn.commit()
    conn.close()

if __name__ == '__main__':
    try:
        migrate()
        print("Migration successful.")
    except Exception as e:
        print(f"Migration failed: {e}")
