import sqlite3

def migrate():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Get existing columns
    cursor.execute('PRAGMA table_info(project_members)')
    columns = [row[1] for row in cursor.fetchall()]
    
    new_columns = {
        'phone': 'TEXT',
        'email': 'TEXT',
        'degree': 'TEXT',
        'year': 'TEXT',
        'grad_year': 'TEXT'
    }
    
    for col, dtype in new_columns.items():
        if col not in columns:
            print(f"Adding column {col}...")
            cursor.execute(f'ALTER TABLE project_members ADD COLUMN {col} {dtype}')
            
    conn.commit()
    conn.close()
    print("Migration completed.")

if __name__ == '__main__':
    migrate()