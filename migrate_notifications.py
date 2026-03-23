import sqlite3

def migrate_notifications():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(notifications)")
    columns = [r[1] for r in cursor.fetchall()]
    print(f"Current columns: {columns}")
    
    if 'title' not in columns:
        print("Adding title...")
        cursor.execute("ALTER TABLE notifications ADD COLUMN title TEXT")
        
    if 'type' not in columns:
        print("Adding type...")
        cursor.execute("ALTER TABLE notifications ADD COLUMN type TEXT DEFAULT 'system'")
        
    if 'content' not in columns:
        print("Adding content...")
        cursor.execute("ALTER TABLE notifications ADD COLUMN content TEXT")
        
    # Migrate message -> content if message exists
    if 'message' in columns and 'content' not in columns:
         # Wait, if I just added content, I can copy now.
         pass
         
    conn.commit()
    
    # Copy data
    if 'message' in columns:
        print("Migrating message to content...")
        cursor.execute("UPDATE notifications SET content = message WHERE content IS NULL")
        conn.commit()
        
    conn.close()
    print("Migration done.")

if __name__ == '__main__':
    migrate_notifications()
