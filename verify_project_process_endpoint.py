import sqlite3
from app import create_app
from config import get_config

cfg = get_config()
conn = sqlite3.connect(cfg.DB_PATH)
conn.row_factory = sqlite3.Row
admin = conn.execute("SELECT id FROM users WHERE role = 'project_admin' ORDER BY id LIMIT 1").fetchone()
uid = admin["id"]
projects = conn.execute(
    "SELECT id, title, project_type FROM projects ORDER BY id ASC LIMIT 10"
).fetchall()
conn.close()

app = create_app()
client = app.test_client()
with client.session_transaction() as s:
    s["user_id"] = uid
    s["role"] = "project_admin"

for p in projects:
    r = client.get(f"/api/projects/{p['id']}/process")
    j = r.get_json()
    data = j.get("data") if isinstance(j, dict) else None
    tpl = data.get("template_name") if isinstance(data, dict) else None
    nodes = data.get("process_structure") if isinstance(data, dict) else None
    print(p["id"], p["project_type"], tpl, nodes)

