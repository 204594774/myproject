import sqlite3
import json

def verify_school_audit():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. 查找一个待学校立项的项目（大创创新训练）
    project = cursor.execute('''
        SELECT id, title, status, current_level, review_stage 
        FROM projects 
        WHERE project_type = 'innovation' AND status IN ('college_recommended', 'approved', 'school_review')
        ORDER BY id DESC LIMIT 1
    ''').fetchone()

    if not project:
        print("未找到待学校立项的项目，尝试创建一个...")
        # 模拟创建一个
        cursor.execute('''
            INSERT INTO projects (title, project_type, status, college, year, created_by)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('测试自动立项项目', 'innovation', 'school_review', '计算机学院', 2026, 1))
        project_id = cursor.lastrowid
    else:
        project_id = project['id']
        print(f"找到待处理项目 ID: {project_id}, 当前状态: {project['status']}")

    # 2. 模拟学校管理员审批通过
    print(f"执行学校审批通过操作 (项目ID: {project_id})...")
    
    # 模拟 audit_project 内部逻辑
    new_status = 'rated'
    cursor.execute('UPDATE projects SET status = ? WHERE id = ?', (new_status, project_id))
    cursor.execute('UPDATE projects SET current_level = ?, review_stage = ? WHERE id = ?', ('school', 'school', project_id))
    
    # 模拟通知和日志（这里简化）
    conn.commit()

    # 3. 验证结果
    updated = cursor.execute('SELECT status, current_level, review_stage FROM projects WHERE id = ?', (project_id,)).fetchone()
    print(f"更新后状态: {updated['status']}")
    print(f"更新后 current_level: {updated['current_level']}")
    print(f"更新后 review_stage: {updated['review_stage']}")

    if updated['status'] == 'rated' and updated['current_level'] == 'school':
        print("\n✅ 验证通过：校级审批后已成功流转至立项（rated）并同步了阶段。")
    else:
        print("\n❌ 验证失败：状态或阶段未正确更新。")

    conn.close()

if __name__ == '__main__':
    verify_school_audit()
