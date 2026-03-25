from app import create_app
import sqlite3

app = create_app()
client = app.test_client()

client.post("/api/login", json={"username": "test_college_admin_cs", "password": "Test123456"})
r = client.put(
    "/api/projects/1/process",
    json={"node_name": "学院赛", "current_status": "已推荐", "comment": "", "award_level": ""},
)
print("process put", r.status_code, r.get_json())

p = client.get("/api/projects/1").get_json()
print("project current_level", p.get("current_level"), "status", p.get("status"))

pr = client.get("/api/projects/1/process").get_json()
print("process node_current_status", pr["data"]["node_current_status"])

conn = sqlite3.connect("database.db")
conn.row_factory = sqlite3.Row
cnt = conn.execute(
    "SELECT COUNT(1) c FROM review_tasks WHERE project_id = 1 AND review_level = 'school'"
).fetchone()["c"]
print("school tasks", cnt)

u = conn.execute(
    "SELECT id FROM users WHERE username = ?", ("test_cc_school_science_judge1",)
).fetchone()
if u:
    n = conn.execute(
        "SELECT COUNT(1) c FROM notifications WHERE user_id = ?", (u["id"],)
    ).fetchone()["c"]
    print("notifications school judge1", n)

