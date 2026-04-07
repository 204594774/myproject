import sqlite3
import os

db_path = r'd:\桌面\new12\instance\app.db'
if not os.path.exists(db_path):
    with open('db_check.txt', 'w') as f: f.write(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("PRAGMA table_info(review_tasks)")
    columns = [col[1] for col in cursor.fetchall()]
    with open('db_check.txt', 'w') as f:
        f.write(f"Columns: {', '.join(columns)}\n")
        if 'not_recommended_reasons' not in columns:
            f.write("Adding column not_recommended_reasons to review_tasks...\n")
            cursor.execute("ALTER TABLE review_tasks ADD COLUMN not_recommended_reasons TEXT")
            conn.commit()
            f.write("Column added successfully.\n")
        else:
            f.write("Column not_recommended_reasons already exists.\n")
except Exception as e:
    with open('db_check.txt', 'w') as f: f.write(f"Error: {e}")
finally:
    conn.close()
