from app import create_app

app = create_app()
client = app.test_client()

client.post("/api/login", json={"username": "test_cc_college_judge1", "password": "Test123456"})

r1 = client.get("/api/reviews/tasks")
print("tasks status", r1.status_code, "count", len(r1.get_json().get("data", [])))

r2 = client.get("/api/projects")
data = r2.get_json().get("data", [])
print("projects status", r2.status_code, "count", len(data))
print([p["id"] for p in data])

