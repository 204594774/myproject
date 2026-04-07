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

entrepreneurship_training = '''{
                    "label": "大学生创新创业训练计划·创业训练项目",
                    "value": "dachuang_entrepreneurship_training",
                    "data": {
                        "title": "大学生创新创业训练计划·创业训练项目",
                        "system_type": "创业体系",
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
                                        { "key": "project_type", "label": "项目类型", "type": "select", "required": true, "system": true, "options": [{ "label": "创业训练", "value": "entrepreneurship_training" }] },
                                        { "key": "extra_info.duration", "label": "研究周期", "type": "select", "required": true, "options": [{ "label": "1年", "value": "1" }, { "label": "2年", "value": "2" }] },
                                        { "key": "college", "label": "所属学院", "type": "select", "required": true, "system": true, "options": [] }
                                    ]
                                },
                                {
                                    "title": "核心内容区",
                                    "fields": [
                                        { "key": "abstract", "label": "项目简介", "type": "richtext", "required": true, "system": true },
                                        { "key": "extra_info.business_model", "label": "商业模式", "type": "richtext", "required": true },
                                        { "key": "extra_info.expected_outcomes", "label": "预期成果", "type": "checkbox", "required": true, "options": [{ "label": "商业计划书", "value": "business_plan" }, { "label": "模拟运营", "value": "mock_operation" }, { "label": "融资", "value": "financing" }, { "label": "公司注册", "value": "company_registration" }] }
                                    ]
                                },
                                {
                                    "title": "财务与团队区",
                                    "fields": [
                                        { "key": "extra_info.budget", "label": "经费预算", "type": "table", "required": true },
                                        { "key": "extra_info.advisors", "label": "指导教师列表", "type": "table", "required": true, "columns": [{ "label": "指导教师姓名", "key": "name", "width": 100 }, { "label": "职称", "key": "title", "width": 100 }, { "label": "所在单位", "key": "org", "width": 160 }, { "label": "指导类型", "key": "type", "width": 100 }], "placeholder": "必须支持动态添加（至少2人，1校内+1校外）" },
                                        { "key": "members", "label": "团队成员", "type": "table", "required": true, "system": true, "columns": [{ "label": "学号", "key": "student_id", "width": 140 }, { "label": "姓名", "key": "name", "width": 100 }, { "label": "年级", "key": "grade", "width": 100 }, { "label": "专业", "key": "major", "width": 160 }, { "label": "角色", "key": "role", "width": 120 }] }
                                    ]
                                },
                                {
                                    "title": "附件材料区",
                                    "fields": [
                                        { "key": "extra_info.attachments.business_plan", "label": "商业计划书", "type": "file", "required": true },
                                        { "key": "extra_info.attachments.stage_achievement", "label": "阶段性成果", "type": "file", "required": false }
                                    ]
                                }
                            ]
                        }
                    }
                }'''

entrepreneurship_practice = '''{
                    "label": "大学生创新创业训练计划·创业实践项目",
                    "value": "dachuang_entrepreneurship_practice",
                    "data": {
                        "title": "大学生创新创业训练计划·创业实践项目",
                        "system_type": "创业体系",
                        "competition_level": "C类",
                        "national_organizer": "教育部高等教育司",
                        "school_organizer": "各学院",
                        "level": "Provincial",
                        "template_type": "practice",
                        "form_config": {
                            "groups": [
                                {
                                    "title": "项目基础信息区",
                                    "fields": [
                                        { "key": "title", "label": "项目名称", "type": "text", "required": true, "system": true },
                                        { "key": "project_type", "label": "项目类型", "type": "select", "required": true, "system": true, "options": [{ "label": "创业实践", "value": "entrepreneurship_practice" }] },
                                        { "key": "extra_info.duration", "label": "研究周期", "type": "select", "required": true, "options": [{ "label": "1年", "value": "1" }, { "label": "2年", "value": "2" }] },
                                        { "key": "college", "label": "所属学院", "type": "select", "required": true, "system": true, "options": [] }
                                    ]
                                },
                                {
                                    "title": "核心内容区",
                                    "fields": [
                                        { "key": "abstract", "label": "项目简介", "type": "richtext", "required": true, "system": true },
                                        { "key": "extra_info.business_model", "label": "商业模式", "type": "richtext", "required": true },
                                        { "key": "extra_info.expected_outcomes", "label": "预期成果", "type": "checkbox", "required": true, "options": [{ "label": "公司注册", "value": "company_registration" }, { "label": "融资", "value": "financing" }, { "label": "营收", "value": "revenue" }, { "label": "专利", "value": "patent" }] }
                                    ]
                                },
                                {
                                    "title": "财务与团队区",
                                    "fields": [
                                        { "key": "extra_info.budget", "label": "经费预算", "type": "table", "required": true },
                                        { "key": "extra_info.advisors", "label": "指导教师列表", "type": "table", "required": true, "columns": [{ "label": "指导教师姓名", "key": "name", "width": 100 }, { "label": "职称", "key": "title", "width": 100 }, { "label": "所在单位", "key": "org", "width": 160 }, { "label": "指导类型", "key": "type", "width": 100 }], "placeholder": "必须支持动态添加（至少2人，1校内+1校外）" },
                                        { "key": "members", "label": "团队成员", "type": "table", "required": true, "system": true, "columns": [{ "label": "学号", "key": "student_id", "width": 140 }, { "label": "姓名", "key": "name", "width": 100 }, { "label": "年级", "key": "grade", "width": 100 }, { "label": "专业", "key": "major", "width": 160 }, { "label": "角色", "key": "role", "width": 120 }] },
                                        { "key": "extra_info.equity_structure", "label": "股权结构", "type": "table", "required": true, "columns": [{ "label": "股东名称", "key": "name", "width": 140 }, { "label": "持股比例", "key": "ratio", "width": 100 }, { "label": "出资方式", "key": "method", "width": 140 }] }
                                    ]
                                },
                                {
                                    "title": "附件材料区",
                                    "fields": [
                                        { "key": "extra_info.attachments.business_plan", "label": "商业计划书", "type": "file", "required": true },
                                        { "key": "extra_info.attachments.business_license", "label": "营业执照", "type": "file", "required": true },
                                        { "key": "extra_info.attachments.stage_achievement", "label": "阶段性成果", "type": "file", "required": false }
                                    ]
                                }
                            ]
                        }
                    }
                }'''

content = replace_preset(content, 'dachuang_entrepreneurship_training', entrepreneurship_training)
content = replace_preset(content, 'dachuang_entrepreneurship_practice', entrepreneurship_practice)

# Also update the cnmu_2026_dachuang_entrepreneurship_training and practice
cnmu_training = entrepreneurship_training.replace('"value": "dachuang_entrepreneurship_training"', '"value": "cnmu_2026_dachuang_entrepreneurship_training"').replace('"label": "大学生创新创业训练计划·创业训练项目"', '"label": "2026大创创业训练项目（中南民大）"')
cnmu_practice = entrepreneurship_practice.replace('"value": "dachuang_entrepreneurship_practice"', '"value": "cnmu_2026_dachuang_entrepreneurship_practice"').replace('"label": "大学生创新创业训练计划·创业实践项目"', '"label": "2026大创创业实践项目（中南民大）"')

content = replace_preset(content, 'cnmu_2026_dachuang_entrepreneurship_training', cnmu_training)
content = replace_preset(content, 'cnmu_2026_dachuang_entrepreneurship_practice', cnmu_practice)

with open('static/js/app.js', 'w', encoding='utf-8') as f:
    f.write(content)
print('Updated entrepreneurship presets')
