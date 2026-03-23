import sqlite3
import os

DB_PATH = r'd:\桌面\new11\database.db'

def dump_all():
    print(f"Dumping projects from {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print("DB file not found")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM projects")
        rows = cursor.fetchall()
        print(f"Total projects: {len(rows)}")
        for row in rows:
            print(dict(row))
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    dump_all()
