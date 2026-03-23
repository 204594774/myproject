import sqlite3
import os

db_path = 'd:/桌面/new11/database.db'
if not os.path.exists(db_path):
    print(f"Error: {db_path} not found")
    exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("--- Checking Projects ---")
projects = cursor.execute("SELECT id, title, status FROM projects WHERE id IN (6, 7, 8, 9, 21, 20, 23)").fetchall()
for p in projects:
    print(f"Project ID: {p['id']}, Title: {p['title']}, Status: {p['status']}")

print("\n--- Checking Competitions ---")
try:
    competitions = cursor.execute("SELECT * FROM competitions").fetchall()
    for c in competitions:
        print(f"Comp ID: {c['id']}, Title: {c['title']}, Status: {c['status']}")
except Exception as e:
    print(f"Error checking competitions: {e}")

print("\n--- Checking User Competitions (Registrations) ---")
try:
    # Assuming there's a table linking users/projects to competitions
    # It might be 'user_competitions' or similar
    tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    table_names = [t['name'] for t in tables]
    print(f"Tables: {table_names}")
    
    if 'user_competitions' in table_names:
        ucs = cursor.execute("SELECT * FROM user_competitions").fetchall()
        for uc in ucs:
            print(dict(uc))
except Exception as e:
    print(f"Error checking user competitions: {e}")

conn.close()
