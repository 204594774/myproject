import sqlite3
conn = sqlite3.connect('database.db')
c = conn.cursor()
res = c.execute("SELECT id, username FROM users WHERE username='student1'").fetchone()
print(f"Student1 ID: {res}")
conn.close()
