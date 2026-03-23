
import sqlite3

def check_users():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    users = conn.execute('SELECT id, username, role FROM users').fetchall()
    print("--- Users ---")
    for u in users:
        print(f"ID: {u['id']}, Username: {u['username']}, Role: {u['role']}")
    conn.close()

if __name__ == '__main__':
    check_users()
