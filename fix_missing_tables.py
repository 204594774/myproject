import sqlite3

def fix_tables():
    conn = sqlite3.connect('database.db')
    
    # 1. Project Files
    print("Creating project_files...")
    conn.execute('''
        CREATE TABLE IF NOT EXISTS project_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            file_type TEXT NOT NULL, -- application, midterm, conclusion
            file_path TEXT NOT NULL,
            original_filename TEXT,
            status TEXT DEFAULT 'pending', -- pending, approved, rejected
            feedback TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
        )
    ''')

    # 2. Project Reviews
    print("Creating project_reviews...")
    conn.execute('''
        CREATE TABLE IF NOT EXISTS project_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            judge_id INTEGER NOT NULL,
            score INTEGER,
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
            FOREIGN KEY (judge_id) REFERENCES users (id)
        )
    ''')

    # 3. Announcements
    print("Creating announcements...")
    conn.execute('''
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            type TEXT DEFAULT 'news', -- news, notice
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Tables fixed.")

if __name__ == '__main__':
    fix_tables()
