import sqlite3
import json

def update_templates():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # 1. Big Challenge (大挑)
    big_challenge_flow = ["学院赛", "校赛", "省赛", "国赛"]
    cursor.execute("UPDATE process_templates SET process_structure = ?, has_mid_check = 0, has_final_acceptance = 0 WHERE template_name = ?", 
                   (json.dumps(big_challenge_flow), "大挑"))
    cursor.execute("SELECT id FROM process_templates WHERE template_name = '大挑'")
    big_id = cursor.fetchone()[0]
    
    big_nodes = [
        ("学院赛", ["待评审", "已推荐", "未推荐"]),
        ("校赛", ["待评审", "已推荐", "未推荐"]),
        ("省赛", ["待评审", "已晋级", "未晋级"]),
        ("国赛", ["待评审", "已获奖", "未获奖"])
    ]
    for node, opts in big_nodes:
        cursor.execute("INSERT OR REPLACE INTO process_node_status (template_id, node_name, status_options) VALUES (?, ?, ?)", 
                       (big_id, node, json.dumps(opts)))

    # 2. Innovation/Entrepreneurship projects (大创项目)
    # The user requested 3 templates: 创新训练, 创业训练, 创业实践
    innovation_flow = ["申报", "学院评审", "学校立项", "中期检查", "结题验收", "结题成绩"]
    innovation_nodes = [
        ("申报", ["待提交", "待导师审核", "导师通过", "导师驳回"]),
        ("学院评审", ["待评审", "通过", "驳回"]),
        ("学校立项", ["待立项", "已立项", "驳回"]),
        ("中期检查", ["待提交", "待审核", "通过", "需整改", "不通过"]),
        ("结题验收", ["待提交", "待审核", "通过", "不通过"]),
        ("结题成绩", ["优秀", "良好", "合格", "不合格"])
    ]
    
    for t_name in ["大创创新训练", "大创创业训练", "大创创业实践"]:
        cursor.execute("UPDATE process_templates SET process_structure = ?, has_mid_check = 1, has_final_acceptance = 1 WHERE template_name = ?", 
                       (json.dumps(innovation_flow), t_name))
        cursor.execute("SELECT id FROM process_templates WHERE template_name = ?", (t_name,))
        res = cursor.fetchone()
        if res:
            tpl_id = res[0]
            for node, opts in innovation_nodes:
                cursor.execute("INSERT OR REPLACE INTO process_node_status (template_id, node_name, status_options) VALUES (?, ?, ?)", 
                               (tpl_id, node, json.dumps(opts)))

    # 3. National Innovation, Small Challenge, SanChuang Regular, SanChuang Practical
    standard_flow = ["校赛", "省赛", "国赛"]
    standard_nodes = [
        ("校赛", ["待评审", "已推荐", "未推荐"]),
        ("省赛", ["待评审", "已晋级", "未晋级"]),
        ("国赛", ["待评审", "已获奖", "未获奖"])
    ]
    
    for t_name in ["国创赛", "小挑", "三创赛常规赛", "三创赛实战赛"]:
        cursor.execute("UPDATE process_templates SET process_structure = ?, has_mid_check = 0, has_final_acceptance = 0 WHERE template_name = ?", 
                       (json.dumps(standard_flow), t_name))
        cursor.execute("SELECT id FROM process_templates WHERE template_name = ?", (t_name,))
        res = cursor.fetchone()
        if res:
            tpl_id = res[0]
            for node, opts in standard_nodes:
                cursor.execute("INSERT OR REPLACE INTO process_node_status (template_id, node_name, status_options) VALUES (?, ?, ?)", 
                               (tpl_id, node, json.dumps(opts)))

    conn.commit()
    conn.close()
    print("All 8 template workflows updated successfully.")

if __name__ == "__main__":
    update_templates()
