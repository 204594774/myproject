import sqlite3

def check_notifications():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check notifications for user 4 (sch_approver)
    notifs = cursor.execute("SELECT * FROM notifications WHERE user_id = 4 ORDER BY created_at DESC").fetchall()
    print(f"Notifications for user 4 (sch_approver): {len(notifs)}")
    for n in notifs:
        print(f"  - [{n['created_at']}] {n['title']}: {n['content']}")

    conn.close()

if __name__ == '__main__':
    check_notifications()
