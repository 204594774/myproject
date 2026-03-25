import sqlite3

conn = sqlite3.connect("database.db")
conn.row_factory = sqlite3.Row

rows = conn.execute(
    "SELECT username, COUNT(1) AS c FROM users WHERE username LIKE 'test_%' GROUP BY username HAVING COUNT(1) > 1 ORDER BY c DESC"
).fetchall()
print("duplicate usernames:", len(rows))
for r in rows:
    print(dict(r))

