import sqlite3
from app import create_app
from config import get_config

cfg = get_config()
conn = sqlite3.connect(cfg.DB_PATH)
conn.row_factory = sqlite3.Row
uid = conn.execute("SELECT id FROM users WHERE role = 'project_admin' ORDER BY id LIMIT 1").fetchone()["id"]

ptypes = [
    "challenge_cup",
    "innovation",
    "internet_plus",
    "youth_challenge",
    "entrepreneurship_training",
    "entrepreneurship_practice",
    "three_creativity_regular",
    "three_creativity_practical",
]

inserted = []
for ptype in ptypes:
    cur = conn.execute(
        "INSERT INTO projects (title, created_by, project_type) VALUES (?, ?, ?)",
        (f"test-{ptype}", uid, ptype),
    )
    inserted.append(cur.lastrowid)
conn.commit()
conn.close()

app = create_app()
client = app.test_client()
with client.session_transaction() as s:
    s["user_id"] = uid
    s["role"] = "project_admin"

for pid, ptype in zip(inserted, ptypes):
    r = client.get(f"/api/projects/{pid}/process")
    j = r.get_json()
    data = j.get("data") if isinstance(j, dict) else None
    if not isinstance(data, dict) or "template_name" not in data:
        print(ptype, r.status_code, j)
        continue
    print(ptype, r.status_code, data["template_name"], len(data["process_structure"]))

conn = sqlite3.connect(cfg.DB_PATH)
for pid in inserted:
    conn.execute("DELETE FROM projects WHERE id = ?", (pid,))
conn.commit()
conn.close()
