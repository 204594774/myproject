import sqlite3

conn = sqlite3.connect("database.db")
conn.row_factory = sqlite3.Row

u = conn.execute("SELECT id FROM users WHERE username = ?", ("test_cc_college_judge1",)).fetchone()
print("uid", u["id"] if u else None)

if u:
    rows = conn.execute(
        "SELECT id, project_id, judge_id, review_level, team_id, status, score FROM review_tasks WHERE judge_id = ? ORDER BY id DESC",
        (u["id"],),
    ).fetchall()
    print("tasks", len(rows))
    for r in rows[:20]:
        print(dict(r))

