from app import create_app

app = create_app()
client = app.test_client()

client.post("/api/login", json={"username": "test_college_admin_cs", "password": "Test123456"})

r1 = client.put("/api/projects/1/process", json={"node_name": "学院赛", "current_status": "已推荐", "comment": "", "award_level": ""})
print("set approved", r1.status_code, r1.get_json())

r2 = client.put("/api/projects/1/process", json={"node_name": "学院赛", "current_status": "未推荐", "comment": "try", "award_level": ""})
print("try change", r2.status_code, r2.get_json())

