import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Check user '张老师'
print("--- User Info ---")
cursor.execute("SELECT id, username, real_name, role, college FROM users WHERE real_name = '张老师'")
user = cursor.fetchone()
print(f"User: {user}")

if user:
    real_name = user[2]
    
    # Check projects for this advisor
    print("\n--- Projects for Advisor ---")
    try:
        cursor.execute("SELECT id, title, advisor_name, status FROM projects WHERE advisor_name = ?", (real_name,))
        projects = cursor.fetchall()
        if not projects:
            print("No projects found for this advisor.")
        for p in projects:
            print(f"Project: {p}")
    except Exception as e:
        print(f"Error querying projects: {e}")
        
    # Check if there are any projects with similar advisor names (maybe whitespace issues?)
    print("\n--- Projects with similar advisor names ---")
    cursor.execute("SELECT id, title, advisor_name, status FROM projects WHERE advisor_name LIKE ?", (f'%{real_name}%',))
    similar_projects = cursor.fetchall()
    for p in similar_projects:
        print(f"Similar Project: {p}")

conn.close()
