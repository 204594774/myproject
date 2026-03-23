import sqlite3

def reset_project(project_id):
    conn = sqlite3.connect('database.db')
    conn.execute("UPDATE projects SET status = 'pending' WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()
    print(f"Project {project_id} reset to 'pending'")

if __name__ == "__main__":
    reset_project(17)
