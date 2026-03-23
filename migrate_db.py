
import sqlite3
import os

def migrate():
    print("Starting database migration...")
    conn = sqlite3.connect('database.db')
    
    # 1. Check and create 'announcements' table if not exists
    try:
        conn.execute('SELECT count(*) FROM announcements')
        print("Table 'announcements' already exists.")
    except sqlite3.OperationalError:
        print("Creating table 'announcements'...")
        conn.execute('''
            CREATE TABLE announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                type TEXT DEFAULT 'news', -- news, notice
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        ''')

    # 2. Check and create 'competitions' table if not exists
    try:
        conn.execute('SELECT count(*) FROM competitions')
        print("Table 'competitions' already exists.")
    except sqlite3.OperationalError:
        print("Creating table 'competitions'...")
        conn.execute('''
            CREATE TABLE competitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                level TEXT,             -- School, Provincial, National
                organizer TEXT,
                registration_start DATE,
                registration_end DATE,
                description TEXT,
                status TEXT DEFAULT 'active', -- active, upcoming, ended
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

    # 3. Check if 'projects' table has 'competition_id' column
    try:
        conn.execute('SELECT competition_id FROM projects LIMIT 1')
        print("Column 'competition_id' in 'projects' already exists.")
    except sqlite3.OperationalError:
        print("Adding column 'competition_id' to 'projects'...")
        try:
            conn.execute('ALTER TABLE projects ADD COLUMN competition_id INTEGER')
        except sqlite3.OperationalError as e:
            print(f"Error adding column: {e}")

    conn.commit()
    conn.close()
    print("Migration completed.")

if __name__ == '__main__':
    migrate()
