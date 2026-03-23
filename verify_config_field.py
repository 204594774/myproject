import sqlite3
import json

def verify_column():
    conn = sqlite3.connect('database.db')
    try:
        # Check if column exists
        cursor = conn.execute("PRAGMA table_info(competitions)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'form_config' in columns:
            print("SUCCESS: form_config column exists in competitions table")
        else:
            print("FAILURE: form_config column MISSING in competitions table")
            
        # Check if data can be inserted
        config = json.dumps({'show_advisor': True})
        try:
            conn.execute("INSERT INTO competitions (title, form_config) VALUES (?, ?)", ('Test Config', config))
            conn.rollback() # Don't actually save test data
            print("SUCCESS: Can insert data into form_config")
        except Exception as e:
            print(f"FAILURE: Cannot insert data: {e}")
            
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    verify_column()