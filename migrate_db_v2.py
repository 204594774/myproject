
import sqlite3
import json

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def migrate_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("Starting database migration...")
    
    # 1. Add columns to projects table
    try:
        # Check if project_level exists
        cursor.execute("SELECT project_level FROM projects LIMIT 1")
    except sqlite3.OperationalError:
        print("Adding project_level column to projects table...")
        cursor.execute("ALTER TABLE projects ADD COLUMN project_level TEXT DEFAULT 'school'")
        
    try:
        # Check if final_grade exists
        cursor.execute("SELECT final_grade FROM projects LIMIT 1")
    except sqlite3.OperationalError:
        print("Adding final_grade column to projects table...")
        cursor.execute("ALTER TABLE projects ADD COLUMN final_grade TEXT")
        
    try:
        # Check if inspiration_source exists
        cursor.execute("SELECT inspiration_source FROM projects LIMIT 1")
    except sqlite3.OperationalError:
        print("Adding inspiration_source column to projects table...")
        cursor.execute("ALTER TABLE projects ADD COLUMN inspiration_source TEXT")

    # 2. Create project_legacy table
    print("Creating project_legacy table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS project_legacy (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_project_id INTEGER,
            title TEXT NOT NULL,
            methodology_summary TEXT,
            expert_comments TEXT,
            ppt_url TEXT,
            borrowed_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 3. Add status column to project_reviews if needed (to track if review is for startup, midterm, or conclusion)
    # Actually, we might need to distinguish review types.
    # Current project_reviews schema: id, project_id, judge_id, score, comment, criteria_scores, created_at
    # We should add 'review_stage' to differentiate between startup, midterm, conclusion reviews.
    try:
        cursor.execute("SELECT review_stage FROM project_reviews LIMIT 1")
    except sqlite3.OperationalError:
        print("Adding review_stage column to project_reviews table...")
        cursor.execute("ALTER TABLE project_reviews ADD COLUMN review_stage TEXT DEFAULT 'startup'")

    conn.commit()
    conn.close()
    print("Database migration completed successfully.")

if __name__ == '__main__':
    migrate_db()
