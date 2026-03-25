import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import sqlite3
from datetime import datetime, timedelta

def check_big_challenge_deadline():
    """检查大挑阶段截止时间，提前3天发送提醒"""
    try:
        conn = sqlite3.connect(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'database.db'))
        conn.row_factory = sqlite3.Row
        
        # 查找所有正在报名的大挑赛事
        comps = conn.execute("SELECT * FROM competitions WHERE template_type = 'challenge_cup' AND registration_end IS NOT NULL AND status = 'active'").fetchall()
        
        now = datetime.now()
        
        for comp in comps:
            try:
                deadline = datetime.strptime(comp['registration_end'], "%Y-%m-%d")
                delta = (deadline - now).days
                
                # 如果距离截止还有 3 天
                if delta == 3:
                    # 查找参与大挑项目的未提交学生
                    pending_projects = conn.execute("SELECT created_by FROM projects WHERE competition_id = ? AND status = 'pending'", (comp['id'],)).fetchall()
                    for p in pending_projects:
                        conn.execute(
                            "INSERT INTO notifications (user_id, title, content, type) VALUES (?, ?, ?, ?)",
                            (p['created_by'], "大挑申报提醒", f"距离【{comp['title']}】申报截止还有3天，请尽快完成并提交申报！", "warning")
                        )
                        print(f"提醒已发送给用户: {p['created_by']}")
            except ValueError:
                pass # Date parse error
                
        conn.commit()
        conn.close()
        print("大挑截止提醒检查完毕")
    except Exception as e:
        print(f"检查出错: {str(e)}")

if __name__ == '__main__':
    check_big_challenge_deadline()