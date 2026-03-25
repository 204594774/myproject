import sqlite3

conn = sqlite3.connect("database.db")
conn.row_factory = sqlite3.Row

users = conn.execute(
    "SELECT username, role, real_name, college, department, status FROM users WHERE username LIKE 'test_%' ORDER BY username"
).fetchall()
print("test users", len(users))
for u in users:
    print(dict(u))

teams = conn.execute(
    "SELECT id, name, level, college, discipline_group, enabled FROM review_teams ORDER BY id"
).fetchall()
print("teams", len(teams))
for t in teams:
    print(dict(t))

