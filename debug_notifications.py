
import sqlite3

def check_users():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    
    print("--- Users ---")
    users = conn.execute("SELECT id, username, real_name, role, college FROM users").fetchall()
    for u in users:
        print(f"ID: {u['id']}, User: {u['username']}, Name: {u['real_name']}, Role: {u['role']}, College: {u['college']}")
        
    print("\n--- Projects ---")
    projects = conn.execute("SELECT id, title, advisor_name, college, created_by FROM projects").fetchall()
    for p in projects:
        print(f"ID: {p['id']}, Title: {p['title']}, Advisor: {p['advisor_name']}, College: {p['college']}")
        
    print("\n--- Notifications ---")
    notifs = conn.execute("SELECT id, user_id, title, content FROM notifications").fetchall()
    for n in notifs:
        print(f"ID: {n['id']}, UserID: {n['user_id']}, Title: {n['title']}, Content: {n['content']}")

    conn.close()

if __name__ == "__main__":
    check_users()
