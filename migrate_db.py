import sqlite3
import os

db_path = r'd:\桌面\new12\database.db'
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("PRAGMA table_info(review_tasks)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'not_recommended_reasons' not in columns:
        print("Adding column not_recommended_reasons to review_tasks...")
        cursor.execute("ALTER TABLE review_tasks ADD COLUMN not_recommended_reasons TEXT")
        conn.commit()
        print("Column added successfully.")
    else:
        print("Column not_recommended_reasons already exists.")
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
