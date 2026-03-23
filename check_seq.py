import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')

def check_sequence():
    print(f"Checking sqlite_sequence in {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print("Database file not found!")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        
        # Check sqlite_sequence table
        try:
            seq_rows = conn.execute("SELECT * FROM sqlite_sequence").fetchall()
            print("\n--- sqlite_sequence ---")
            for row in seq_rows:
                print(f"Table: {row['name']} | Seq: {row['seq']}")
        except Exception as e:
            print(f"Error reading sqlite_sequence: {e}")

        # Check projects table for max ID
        try:
            max_id = conn.execute("SELECT MAX(id) FROM projects").fetchone()[0]
            print(f"\nMax ID in projects table: {max_id}")
            
            # List all IDs to see gaps
            all_ids = conn.execute("SELECT id FROM projects ORDER BY id").fetchall()
            ids = [r['id'] for r in all_ids]
            print(f"Existing IDs: {ids}")
            
        except Exception as e:
            print(f"Error checking projects table: {e}")

        conn.close()
    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == '__main__':
    check_sequence()
