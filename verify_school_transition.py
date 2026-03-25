from app import create_app
import sqlite3

app = create_app()
client = app.test_client()

client.post("/api/login", json={"username": "test_school_admin", "password": "Test123456"})

r = client.put(
    "/api/projects/1/process",
    json={"node_name": "校赛", "current_status": "已推荐", "comment": "", "award_level": ""},
)
print("set school recommended", r.status_code, r.get_json())

conn = sqlite3.connect("database.db")
conn.row_factory = sqlite3.Row
p = conn.execute(
    "SELECT current_level, review_stage, school_review_result FROM projects WHERE id = 1"
).fetchone()
print("project", dict(p))

statuses = conn.execute(
    "SELECT node_name, current_status FROM project_node_status WHERE project_id = 1 ORDER BY node_name"
).fetchall()
print("nodes", [dict(s) for s in statuses])

try_change = client.put(
    "/api/projects/1/process",
    json={"node_name": "校赛", "current_status": "未推荐", "comment": "try", "award_level": ""},
)
print("try change after lock", try_change.status_code, try_change.get_json())

