import sqlite3

def migrate():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Check existing columns
    cursor.execute("PRAGMA table_info(projects)")
    columns = [r[1] for r in cursor.fetchall()]
    print(f"Current columns: {columns}")
    
    # Add abstract
    if 'abstract' not in columns:
        print("Adding abstract column...")
        cursor.execute("ALTER TABLE projects ADD COLUMN abstract TEXT")
    else:
        print("abstract column already exists.")

    # Add assessment_indicators
    if 'assessment_indicators' not in columns:
        print("Adding assessment_indicators column...")
        cursor.execute("ALTER TABLE projects ADD COLUMN assessment_indicators TEXT")
    else:
        print("assessment_indicators column already exists.")

    conn.commit()
    conn.close()

if __name__ == '__main__':
    try:
        migrate()
        print("Migration successful.")
    except Exception as e:
        print(f"Migration failed: {e}")
