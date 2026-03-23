import sqlite3

def migrate():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Check existing columns
    cursor.execute("PRAGMA table_info(innovation_projects)")
    columns = [r[1] for r in cursor.fetchall()]
    print(f"Current columns: {columns}")
    
    # Add risk_control
    if 'risk_control' not in columns:
        print("Adding risk_control column...")
        cursor.execute("ALTER TABLE innovation_projects ADD COLUMN risk_control TEXT")
    else:
        print("risk_control column already exists.")

    conn.commit()
    conn.close()

if __name__ == '__main__':
    try:
        migrate()
        print("Migration successful.")
    except Exception as e:
        print(f"Migration failed: {e}")
