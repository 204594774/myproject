import json
import re

with open('static/js/app.js', 'r', encoding='utf-8') as f:
    content = f.read()

def replace_preset(content, preset_value, new_preset_str):
    pattern = r'\{\s*\"label\"[^\}]+\"value\"\s*:\s*\"' + preset_value + r'\"'
    match = re.search(pattern, content)
    if not match:
        print(f'Preset {preset_value} not found')
        return content
    
    start_idx = match.start()
    bracket_count = 0
    end_idx = -1
    for i in range(start_idx, len(content)):
        if content[i] == '{':
            bracket_count += 1
        elif content[i] == '}':
            bracket_count -= 1
            if bracket_count == 0:
                end_idx = i + 1
                break
                
    if end_idx != -1:
        return content[:start_idx] + new_preset_str + content[end_idx:]
    return content

new_innovation = '''{
                    "label": "大学生创新创业训练计划·创新训练项目",
                    "value": "innovation_training",
                    "data": {
                        "title": "大学生创新创业训练计划·创新训练项目",
                        "system_type": "创新体系",
                        "competition_level": "C类",
                        "national_organizer": "教育部高等教育司",
                        "school_organizer": "各学院",
                        "level": "Provincial",
                        "template_type": "training",
                        "form_config": {
                            "groups": [
                                {
                                    "title": "项目基础信息区",
                                    "fields": [
                                        { "key": "title", "label": "项目名称", "type": "text", "required": true, "system": true },
                                        { "key": "project_type", "label": "项目类型", "type": "select", "required": true, "system": true, "options": [{ "label": "创新训练", "value": "innovation" }] },
                                        { "key": "extra_info.duration", "label": "研究周期", "type": "select", "required": true, "options": [{ "label": "1年", "value": "1" }, { "label": "2年", "value": "2" }] },
                                        { "key": "college", "label": "所属学院", "type": "select", "required": true, "system": true, "options": [] },
                                        { "key": "extra_info.topic_source", "label": "选题来源", "type": "select", "required": true, "options": [{ "label": "自主选题", "value": "自主选题" }, { "label": "教师科研", "value": "教师科研" }, { "label": "社会委托", "value": "社会委托" }, { "label": "毕设选题", "value": "毕设选题" }, { "label": "学院发布", "value": "学院发布" }, { "label": "揭榜挂帅", "value": "揭榜挂帅" }] },
                                        { "key": "extra_info.is_jiebang", "label": "是否“揭榜挂帅”专项", "type": "radio", "required": true, "options": [{ "label": "是", "value": "是" }, { "label": "否", "value": "否" }] },
                                        { "key": "extra_info.is_key_support_candidate", "label": "重点支持项目", "type": "radio", "required": false, "options": [{ "label": "是", "value": "是" }, { "label": "否", "value": "否" }] }
                                    ]
                                },
                                {
                                    "title": "核心内容区",
                                    "fields": [
                                        { "key": "abstract", "label": "项目简介", "type": "richtext", "required": true, "system": true },
                                        { "key": "extra_info.innovation_points", "label": "创新点描述", "type": "richtext", "required": true },
                                        { "key": "extra_info.research_plan", "label": "研究方案与技术路线", "type": "richtext", "required": true },
                                        { "key": "extra_info.implementation_conditions", "label": "实施条件", "type": "richtext", "required": true },
                                        { "key": "extra_info.expected_outcomes", "label": "预期成果", "type": "checkbox", "required": true, "options": [{ "label": "论文", "value": "paper" }, { "label": "专利", "value": "patent" }, { "label": "软著", "value": "software" }, { "label": "实物", "value": "product" }, { "label": "调研报告", "value": "report" }] }
                                    ]
                                },
                                {
                                    "title": "经费与团队区",
                                    "fields": [
                                        { "key": "extra_info.budget", "label": "经费预算", "type": "table", "required": true },
                                        { "key": "advisor_name", "label": "指导教师姓名", "type": "text", "required": true, "system": true },
                                        { "key": "extra_info.advisor_title", "label": "指导教师职称", "type": "select", "required": true, "options": [{ "label": "教授", "value": "教授" }, { "label": "副教授", "value": "副教授" }, { "label": "讲师", "value": "讲师" }, { "label": "助教", "value": "助教" }] },
                                        { "key": "extra_info.advisor_org", "label": "指导教师所在单位", "type": "text", "required": true },
                                        { "key": "members", "label": "团队成员", "type": "table", "required": true, "system": true, "columns": [{ "label": "学号", "key": "student_id", "width": 140 }, { "label": "姓名", "key": "name", "width": 100 }, { "label": "年级", "key": "grade", "width": 100 }, { "label": "专业", "key": "major", "width": 160 }, { "label": "角色", "key": "role", "width": 120 }] }
                                    ]
                                },
                                {
                                    "title": "附件材料区",
                                    "fields": [
                                        { "key": "extra_info.attachments.application_doc", "label": "申报书", "type": "file", "required": true, "placeholder": "PDF格式" },
                                        { "key": "extra_info.attachments.stage_achievement", "label": "已有阶段性成果", "type": "file", "required": false, "placeholder": "重点支持项目必填", "show_if": { "key": "extra_info.is_key_support_candidate", "values": ["是"] } },
                                        { "key": "extra_info.attachments.other_support", "label": "其他支撑材料", "type": "file", "required": false }
                                    ]
                                }
                            ]
                        }
                    }
                }'''

content = replace_preset(content, 'innovation_training', new_innovation)

new_innovation_cnmu = new_innovation.replace('"value": "innovation_training"', '"value": "cnmu_2026_dachuang_innovation"').replace('"label": "大学生创新创业训练计划·创新训练项目"', '"label": "2026大创创新训练项目（中南民大）"')
content = replace_preset(content, 'cnmu_2026_dachuang_innovation', new_innovation_cnmu)

with open('static/js/app.js', 'w', encoding='utf-8') as f:
    f.write(content)
print('Updated app.js presets')
