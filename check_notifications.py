import sqlite3

def check_notifications():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notifications WHERE user_id = 4")
    notifs = cursor.fetchall()
    print("Notifications for user 4:", notifs)
    conn.close()

if __name__ == '__main__':
    check_notifications()
