from app import create_app

app = create_app()
client = app.test_client()

def login(username, password):
    r = client.post("/api/login", json={"username": username, "password": password})
    return r.status_code, r.get_json()

for u in [
    "test_college_admin_cs",
    "test_school_admin",
    "test_cc_college_leader",
    "test_cc_school_social_leader",
    "test_cc_school_science_leader",
]:
    code, body = login(u, "Test123456")
    print(u, code, body.get("message") if isinstance(body, dict) else body)

