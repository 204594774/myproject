import sqlite3
from werkzeug.security import generate_password_hash

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

cols = [r[1] for r in cursor.execute('PRAGMA table_info(users)').fetchall()]
has_college = 'college' in cols
has_status = 'status' in cols

new_college = "计算机学院（人工智能学院）"
users_to_update = ['col_approver', 'teacher1', 'student1', 'judge1']
users_to_reset_pwd = ['proj_admin', 'col_approver', 'sch_approver', 'judge1', 'teacher1', 'student1']
legacy_users = [
    ('admin', 'system_admin', None),
    ('college', 'college_approver', '123456'),
    ('school', 'school_approver', '123456'),
    ('teacher', 'teacher', '123456'),
    ('student', 'student', '123456'),
    ('test', 'student', '123456')
]

if has_college:
    for user in users_to_update:
        cursor.execute("UPDATE users SET college = ? WHERE username = ?", (new_college, user))

hashed = generate_password_hash('123456')
for user in users_to_reset_pwd:
    if has_status:
        cursor.execute("UPDATE users SET password = ?, status = 'active' WHERE username = ?", (hashed, user))
    else:
        cursor.execute("UPDATE users SET password = ? WHERE username = ?", (hashed, user))

# 激活所有非管理员用户
if has_status:
    cursor.execute("UPDATE users SET status = 'active' WHERE username <> 'admin'")

for uname, new_role, pwd in legacy_users:
    cursor.execute("UPDATE users SET role = ? WHERE username = ?", (new_role, uname))
    if pwd:
        hp = generate_password_hash(pwd)
        if has_status:
            cursor.execute("UPDATE users SET password = ?, status = 'active' WHERE username = ?", (hp, uname))
        else:
            cursor.execute("UPDATE users SET password = ? WHERE username = ?", (hp, uname))

# 确保存在评委账号 judge
exists = cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'judge'").fetchone()[0]
if exists == 0:
    hp = generate_password_hash('123456')
    cursor.execute("INSERT INTO users (username, password, role, real_name) VALUES (?, ?, ?, ?)", ('judge', hp, 'judge', '评委老师'))
    if has_status:
        cursor.execute("UPDATE users SET status = 'active' WHERE username = 'judge'")

conn.commit()
print("Updated users college successfully.")
print("Reset passwords to default for specified users.")
print("Activated all non-admin users.")
print("Normalized legacy user roles and passwords.")
conn.close()
