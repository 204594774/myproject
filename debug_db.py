import sqlite3
import os

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def inspect_db():
    if not os.path.exists('database.db'):
        print("database.db not found!")
        return

    conn = get_db_connection()
    try:
        print("--- Projects Table (Detailed ID Inspection) ---")
        projects = conn.execute('SELECT id, title, status, created_by FROM projects').fetchall()
        for p in projects:
            raw_id = p['id']
            print(f"ID: {repr(raw_id)} (Type: {type(raw_id)}), Title: {p['title']}")
            
        print("\n--- Project Members ---")
        members = conn.execute('SELECT project_id, name, is_leader FROM project_members').fetchall()
        for m in members:
            print(f"ProjectID: {m['project_id']}, Name: {m['name']}, Leader: {m['is_leader']}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    inspect_db()
