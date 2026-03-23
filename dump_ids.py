import sqlite3

def check_ids():
    try:
        conn = sqlite3.connect(r'D:\桌面\new11\database.db')
        conn.row_factory = sqlite3.Row
        rows = conn.execute('SELECT id, title, created_by, college, status FROM projects').fetchall()
        print(f"Total projects: {len(rows)}")
        for row in rows:
            print(f"ID: {row['id']}, Title: {row['title']}, College: {row['college']}, Status: {row['status']}")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    check_ids()
