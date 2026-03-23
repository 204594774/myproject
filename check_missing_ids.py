import sqlite3
import os

db_path = r'D:\桌面\new11\database.db'
if not os.path.exists(db_path):
    print(f"Error: {db_path} not found")
    exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

ids_to_check = [6, 10, 11, 13, 14, 15, 17, 18]
print(f"Checking IDs in {db_path}...")
for pid in ids_to_check:
    row = cursor.execute("SELECT id, title, status FROM projects WHERE id = ?", (pid,)).fetchone()
    if row:
        print(f"ID {pid}: FOUND - Title: {row['title']}, Status: {row['status']}")
    else:
        print(f"ID {pid}: MISSING")

print("\nListing all existing projects:")
rows = cursor.execute("SELECT id, title FROM projects").fetchall()
for r in rows:
    print(f"ID {r['id']}: {r['title']}")

conn.close()
