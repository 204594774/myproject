import sqlite3

def check_school_notifications():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Get all school approvers
    approvers = cursor.execute("SELECT id, username, real_name FROM users WHERE role = 'school_approver'").fetchall()
    
    print(f"Found {len(approvers)} school approvers:")
    for app in approvers:
        print(f"ID: {app[0]}, Username: {app[1]}, Name: {app[2]}")
        
        # Get notifications
        notifs = cursor.execute("SELECT id, title, content, is_read, created_at FROM notifications WHERE user_id = ?", (app[0],)).fetchall()
        print(f"  Notifications ({len(notifs)}):")
        for n in notifs:
            print(f"    [{n[0]}] {n[1]} - {n[2]} (Read: {n[3]})")
            
    conn.close()

if __name__ == "__main__":
    check_school_notifications()
