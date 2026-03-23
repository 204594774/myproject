import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Check user '张老师'
print("--- User Info ---")
cursor.execute("SELECT id, username, real_name, role, college FROM users WHERE real_name = '张老师'")
user = cursor.fetchone()
print(f"User: {user}")

if user:
    user_id = user[0]
    real_name = user[2]
    
    # Check projects for this advisor
    print("\n--- Projects for Advisor ---")
    cursor.execute("SELECT id, title, advisor_name, status, project_status FROM projects WHERE advisor_name = ?", (real_name,))
    projects = cursor.fetchall()
    for p in projects:
        print(f"Project: {p}")
        
    # Also check if there are any projects at all
    print("\n--- All Projects Sample ---")
    cursor.execute("SELECT id, title, advisor_name FROM projects LIMIT 5")
    all_projects = cursor.fetchall()
    for p in all_projects:
        print(f"Sample Project: {p}")

else:
    print("User '张老师' not found.")
    
    # List all teachers
    print("\n--- All Teachers ---")
    cursor.execute("SELECT id, username, real_name FROM users WHERE role = 'teacher'")
    teachers = cursor.fetchall()
    for t in teachers:
        print(f"Teacher: {t}")

conn.close()
