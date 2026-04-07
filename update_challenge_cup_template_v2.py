import sqlite3
import json

def update_template():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # 1. Update Template structure
    new_structure = ["指导教师初审", "学院赛", "校赛", "省赛", "国赛"]
    cursor.execute("UPDATE process_templates SET process_structure = ? WHERE template_name = ?", (json.dumps(new_structure), "大挑"))
    
    # Get template ID
    cursor.execute("SELECT id FROM process_templates WHERE template_name = '大挑'")
    tpl_id = cursor.fetchone()[0]
    
    # 2. Add node status options
    nodes = [
        ("指导教师初审", ["待初审", "已通过", "已驳回"]),
        ("学院赛", ["待评审", "已推荐", "未推荐"]),
        ("校赛", ["待评审", "拟推荐", "已获校奖", "不通过"]),
        ("省赛", ["待评审", "已获省奖", "已晋级国赛", "未获奖"]),
        ("国赛", ["待评审", "已获国奖", "未获奖"])
    ]
    
    for node_name, options in nodes:
        cursor.execute("INSERT OR REPLACE INTO process_node_status (template_id, node_name, status_options) VALUES (?, ?, ?)", 
                       (tpl_id, node_name, json.dumps(options)))
    
    conn.commit()
    conn.close()
    print("大挑模板过程节点更新完成 (保留 学院赛/校赛 名称)")

if __name__ == "__main__":
    update_template()
