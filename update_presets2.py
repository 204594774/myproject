import json

presets = [
    # ---- 创新体系 ----
    {
        "label": "大挑（课外学术科技作品竞赛）",
        "value": "da_tiao",
        "data": {
            "title": "“挑战杯”全国大学生课外学术科技作品竞赛",
            "system_type": "创新体系",
            "competition_level": "A类",
            "national_organizer": "共青团中央、中国科协、教育部、中国社科院、全国学联等",
            "school_organizer": "校团委",
            "level": "National",
            "template_type": "competition",
            "form_config": {
                "groups": [
                    {
                        "title": "作品基础信息",
                        "fields": [
                            {"key": "title", "label": "作品名称", "type": "text", "required": True, "system": True},
                            {"key": "extra_info.category", "label": "作品类别", "type": "select", "required": True, "options": [{"label": "自然科学类学术论文", "value": "natural_science"}, {"label": "哲学社会科学类社会调查报告", "value": "social_science"}, {"label": "科技发明制作", "value": "tech_invention"}]},
                            {"key": "extra_info.subject", "label": "所属学科", "type": "select", "required": True, "options": [{"label": "机械与控制", "value": "mech"}, {"label": "信息技术", "value": "it"}, {"label": "数理", "value": "math"}, {"label": "生命科学", "value": "life"}, {"label": "能源化工", "value": "energy"}]}
                        ]
                    },
                    {
                        "title": "核心内容",
                        "fields": [
                            {"key": "abstract", "label": "作品简介", "type": "richtext", "required": True, "system": True, "placeholder": "限制500字以内"},
                            {"key": "extra_info.background", "label": "研究背景", "type": "richtext", "required": True},
                            {"key": "extra_info.methodology", "label": "研究方法", "type": "textarea", "required": True},
                            {"key": "extra_info.innovation", "label": "创新点", "type": "textarea", "required": True},
                            {"key": "extra_info.application_value", "label": "应用价值", "type": "textarea", "required": False}
                        ]
                    },
                    {
                        "title": "团队信息",
                        "fields": [
                            {"key": "members", "label": "团队成员", "type": "table", "required": True, "system": True},
                            {"key": "advisor_name", "label": "指导教师", "type": "text", "required": True, "system": True}
                        ]
                    },
                    {
                        "title": "附件材料",
                        "fields": [
                            {"key": "extra_info.attachments.full_paper", "label": "论文/报告全文", "type": "file", "required": True, "placeholder": "PDF格式，≤20M"},
                            {"key": "extra_info.attachments.plagiarism_report", "label": "查重报告", "type": "file", "required": True, "placeholder": "PDF格式"},
                            {"key": "extra_info.attachments.support_materials", "label": "支撑材料", "type": "file", "required": False, "placeholder": "图片、数据等"}
                        ]
                    }
                ]
            }
        }
    },
    {
        "label": "数学建模/电子设计等学科竞赛",
        "value": "math_modeling",
        "data": {
            "title": "全国大学生数学建模竞赛",
            "system_type": "创新体系",
            "competition_level": "B类",
            "national_organizer": "中国工业与应用数学学会",
            "school_organizer": "数学与统计学学院",
            "level": "National",
            "template_type": "competition",
            "form_config": {
                "groups": [
                    {
                        "title": "项目基础信息",
                        "fields": [
                            {"key": "title", "label": "项目名称", "type": "text", "required": True, "system": True},
                            {"key": "extra_info.competition_type", "label": "竞赛类型", "type": "select", "required": True, "options": [{"label": "数学建模", "value": "math"}, {"label": "电子设计", "value": "electronic"}, {"label": "计算机设计", "value": "computer"}, {"label": "其他", "value": "other"}]}
                        ]
                    },
                    {
                        "title": "核心内容",
                        "fields": [
                            {"key": "abstract", "label": "项目简介", "type": "richtext", "required": True, "system": True},
                            {"key": "extra_info.tech_route", "label": "技术路线", "type": "richtext", "required": True},
                            {"key": "extra_info.innovation", "label": "创新点", "type": "textarea", "required": True}
                        ]
                    },
                    {
                        "title": "团队信息",
                        "fields": [
                            {"key": "members", "label": "团队成员", "type": "table", "required": True, "system": True},
                            {"key": "advisor_name", "label": "指导教师", "type": "text", "required": True, "system": True}
                        ]
                    },
                    {
                        "title": "附件材料",
                        "fields": [
                            {"key": "extra_info.attachments.work_paper", "label": "作品/论文", "type": "file", "required": True, "placeholder": "PDF格式"},
                            {"key": "extra_info.attachments.source_code", "label": "源代码/设计图", "type": "file", "required": False, "placeholder": "压缩包"}
                        ]
                    }
                ]
            }
        }
    },
    {
        "label": "电子设计竞赛",
        "value": "electronic_design",
        "data": {
            "title": "全国大学生电子设计竞赛",
            "system_type": "创新体系",
            "competition_level": "B类",
            "national_organizer": "教育部、工信部",
            "school_organizer": "电子信息工程学院",
            "level": "National",
            "template_type": "competition",
            "form_config": {
                "groups": [
                    {
                        "title": "项目基础信息",
                        "fields": [
                            {"key": "title", "label": "项目名称", "type": "text", "required": True, "system": True},
                            {"key": "extra_info.competition_type", "label": "竞赛类型", "type": "select", "required": True, "options": [{"label": "数学建模", "value": "math"}, {"label": "电子设计", "value": "electronic"}, {"label": "计算机设计", "value": "computer"}, {"label": "其他", "value": "other"}]}
                        ]
                    },
                    {
                        "title": "核心内容",
                        "fields": [
                            {"key": "abstract", "label": "项目简介", "type": "richtext", "required": True, "system": True},
                            {"key": "extra_info.tech_route", "label": "技术路线", "type": "richtext", "required": True},
                            {"key": "extra_info.innovation", "label": "创新点", "type": "textarea", "required": True}
                        ]
                    },
                    {
                        "title": "团队信息",
                        "fields": [
                            {"key": "members", "label": "团队成员", "type": "table", "required": True, "system": True},
                            {"key": "advisor_name", "label": "指导教师", "type": "text", "required": True, "system": True}
                        ]
                    },
                    {
                        "title": "附件材料",
                        "fields": [
                            {"key": "extra_info.attachments.work_paper", "label": "作品/论文", "type": "file", "required": True, "placeholder": "PDF格式"},
                            {"key": "extra_info.attachments.source_code", "label": "源代码/设计图", "type": "file", "required": False, "placeholder": "压缩包"}
                        ]
                    }
                ]
            }
        }
    },
    {
        "label": "大创创新训练项目",
        "value": "innovation_training",
        "data": {
            "title": "大学生创新创业训练计划（创新训练）",
            "system_type": "创新体系",
            "competition_level": "C类",
            "national_organizer": "教育部/教育厅",
            "school_organizer": "各学院",
            "level": "Provincial",
            "template_type": "training",
            "form_config": {
                "groups": [
                    {
                        "title": "项目基础信息区",
                        "fields": [
                            {"key": "title", "label": "项目名称", "type": "text", "required": True, "system": True},
                            {"key": "project_type", "label": "项目类型", "type": "select", "required": True, "system": True, "options": [{"label": "创新训练", "value": "innovation"}]},
                            {"key": "extra_info.duration", "label": "研究周期", "type": "select", "required": True, "options": [{"label": "1年", "value": "1"}, {"label": "2年", "value": "2"}]},
                            {"key": "college", "label": "所属学院", "type": "select", "required": True, "system": True, "options": []},
                            {"key": "extra_info.topic_source", "label": "选题来源", "type": "select", "required": True, "options": [{"label": "自主选题", "value": "自主选题"}, {"label": "教师科研", "value": "教师科研"}, {"label": "社会委托", "value": "社会委托"}, {"label": "毕设选题", "value": "毕设选题"}, {"label": "学院发布", "value": "学院发布"}, {"label": "揭榜挂帅", "value": "揭榜挂帅"}]},
                            {"key": "extra_info.is_jiebang", "label": "是否“揭榜挂帅”专项", "type": "radio", "required": True, "options": [{"label": "是", "value": "是"}, {"label": "否", "value": "否"}]},
                            {"key": "extra_info.is_key_support_candidate", "label": "重点支持项目", "type": "radio", "required": False, "options": [{"label": "是", "value": "是"}, {"label": "否", "value": "否"}], "show_if": {"key": "extra_info.college_recommend_rank", "values": [1]}}
                        ]
                    },
                    {
                        "title": "核心内容区",
                        "fields": [
                            {"key": "abstract", "label": "项目简介", "type": "richtext", "required": True, "system": True},
                            {"key": "extra_info.innovation_points", "label": "创新点描述", "type": "richtext", "required": True},
                            {"key": "extra_info.expected_outcomes", "label": "预期成果", "type": "checkbox", "required": True, "options": [{"label": "论文", "value": "paper"}, {"label": "专利", "value": "patent"}, {"label": "软著", "value": "software"}, {"label": "实物", "value": "product"}, {"label": "调研报告", "value": "report"}]},
                            {"key": "extra_info.research_plan", "label": "研究方案与技术路线", "type": "richtext", "required": True},
                            {"key": "extra_info.implementation_conditions", "label": "实施条件", "type": "richtext", "required": True}
                        ]
                    },
                    {
                        "title": "指导教师信息",
                        "fields": []
                    },
                    {
                        "title": "经费与团队区",
                        "fields": [
                            {"key": "extra_info.budget", "label": "经费预算", "type": "table", "required": True},
                            {"key": "members", "label": "团队成员", "type": "table", "required": True, "system": True, "columns": [{"label": "姓名", "key": "name", "width": 90}, {"label": "学号", "key": "student_id", "width": 120}, {"label": "年级", "key": "grade", "width": 90}, {"label": "专业", "key": "major", "width": 120}, {"label": "学院", "key": "college", "width": 120}, {"label": "联系方式", "key": "contact", "width": 140}]}
                        ]
                    },
                    {
                        "title": "附件材料区",
                        "fields": [
                            {"key": "extra_info.attachments.application_doc", "label": "申报书", "type": "file", "required": True, "placeholder": "PDF格式"},
                            {"key": "extra_info.attachments.stage_achievement", "label": "已有阶段性成果", "type": "file", "required": True, "placeholder": "可选；重点支持项目必填", "show_if": {"key": "extra_info.is_key_support_candidate", "values": ["是"]}}
                        ]
                    }
                ]
            }
        }
    },
    
    # ---- 创业体系 ----
    {
        "label": "互联网+大学生创新创业大赛",
        "value": "internet_plus",
        "data": {
            "title": "中国国际大学生创新大赛（互联网+）",
            "system_type": "创业体系",
            "competition_level": "A类",
            "national_organizer": "教育部等12个部委",
            "school_organizer": "创新创业学院",
            "level": "National",
            "template_type": "competition",
            "form_config": {
                "groups": [
                    {
                        "title": "项目基础信息",
                        "fields": [
                            {"key": "title", "label": "项目名称", "type": "text", "required": True, "system": True},
                            {"key": "extra_info.track", "label": "参赛赛道", "type": "select", "required": True, "options": [{"label": "高教主赛道", "value": "main"}, {"label": "红旅赛道", "value": "red"}, {"label": "产业命题赛道", "value": "industry"}]},
                            {"key": "extra_info.project_type_4new", "label": "项目类型（四新）", "type": "select", "required": True, "options": [{"label": "新工科类", "value": "engineering"}, {"label": "新医科类", "value": "medical"}, {"label": "新农科类", "value": "agriculture"}, {"label": "新文科类", "value": "liberal_arts"}]},
                            {"key": "extra_info.group", "label": "参赛组别", "type": "select", "required": True, "options": [{"label": "本科生创意组", "value": "undergrad_idea"}, {"label": "研究生创意组", "value": "grad_idea"}, {"label": "初创组", "value": "startup"}, {"label": "成长组", "value": "growth"}, {"label": "师生共创组", "value": "teacher_student"}]}
                        ]
                    },
                    {
                        "title": "核心内容",
                        "fields": [
                            {"key": "abstract", "label": "执行概要", "type": "richtext", "required": True, "system": True, "placeholder": "300-500字"},
                            {"key": "extra_info.market_pain_points", "label": "市场痛点分析", "type": "richtext", "required": True},
                            {"key": "extra_info.product_solution", "label": "产品/解决方案", "type": "richtext", "required": True},
                            {"key": "extra_info.business_model", "label": "商业模式", "type": "richtext", "required": True},
                            {"key": "extra_info.core_competitiveness", "label": "核心竞争力", "type": "richtext", "required": True},
                            {"key": "extra_info.operation_status", "label": "运营现状", "type": "richtext", "required": True}
                        ]
                    },
                    {
                        "title": "财务与融资",
                        "fields": [
                            {"key": "extra_info.equity_structure", "label": "股本结构", "type": "table", "required": True},
                            {"key": "extra_info.financing_needs", "label": "融资需求", "type": "table", "required": True},
                            {"key": "extra_info.financial_forecast", "label": "财务预测", "type": "table", "required": True}
                        ]
                    },
                    {
                        "title": "团队信息",
                        "fields": [
                            {"key": "members", "label": "项目成员", "type": "table", "required": True, "system": True},
                            {"key": "advisor_name", "label": "指导教师", "type": "text", "required": True, "system": True}
                        ]
                    },
                    {
                        "title": "附件材料",
                        "fields": [
                            {"key": "extra_info.attachments.business_plan", "label": "商业计划书", "type": "file", "required": True, "placeholder": "PDF格式，≤20M"},
                            {"key": "extra_info.attachments.pitch_deck", "label": "路演PPT", "type": "file", "required": True, "placeholder": "PPT/PPTX格式"},
                            {"key": "extra_info.attachments.video", "label": "1分钟视频", "type": "file", "required": False, "placeholder": "MP4格式（省赛/国赛强制）"}
                        ]
                    }
                ]
            }
        }
    },
    {
        "label": "小挑（创业计划竞赛）",
        "value": "xiao_tiao",
        "data": {
            "title": "“挑战杯”中国大学生创业计划竞赛",
            "system_type": "创业体系",
            "competition_level": "A类",
            "national_organizer": "共青团中央、中国科协、教育部、全国学联等",
            "school_organizer": "校团委（创新创业学院协同）",
            "level": "National",
            "template_type": "competition",
            "form_config": {
                "groups": [
                    {
                        "title": "项目基础信息",
                        "fields": [
                            {"key": "title", "label": "项目名称", "type": "text", "required": True, "system": True},
                            {"key": "extra_info.group", "label": "参赛组别", "type": "select", "required": True, "options": [{"label": "科技创新和未来产业", "value": "tech_innovation"}, {"label": "乡村振兴和农业农村现代化", "value": "rural_revitalization"}, {"label": "社会治理和公共服务", "value": "social_governance"}, {"label": "生态环保和可持续发展", "value": "eco_sustainability"}, {"label": "文化创意和区域合作", "value": "cultural_creative"}]}
                        ]
                    },
                    {
                        "title": "核心内容",
                        "fields": [
                            {"key": "abstract", "label": "执行概要", "type": "richtext", "required": True, "system": True},
                            {"key": "extra_info.market_analysis", "label": "市场分析", "type": "richtext", "required": True},
                            {"key": "extra_info.product_service", "label": "产品/服务", "type": "richtext", "required": True},
                            {"key": "extra_info.business_model", "label": "商业模式", "type": "richtext", "required": True},
                            {"key": "extra_info.financial_analysis", "label": "财务分析", "type": "richtext", "required": True}
                        ]
                    },
                    {
                        "title": "团队信息",
                        "fields": [
                            {"key": "members", "label": "项目成员", "type": "table", "required": True, "system": True},
                            {"key": "advisor_name", "label": "指导教师", "type": "text", "required": True, "system": True}
                        ]
                    },
                    {
                        "title": "附件材料",
                        "fields": [
                            {"key": "extra_info.attachments.business_plan", "label": "商业计划书", "type": "file", "required": True, "placeholder": "PDF格式"},
                            {"key": "extra_info.attachments.pitch_deck", "label": "路演PPT", "type": "file", "required": True, "placeholder": "PPT/PPTX格式"}
                        ]
                    }
                ]
            }
        }
    },
    {
        "label": "大创创业训练/实践项目",
        "value": "entrepreneurship_training",
        "data": {
            "title": "大学生创新创业训练计划（创业类）",
            "system_type": "创业体系",
            "competition_level": "C类",
            "national_organizer": "教育部/教育厅",
            "school_organizer": "创新创业学院",
            "level": "Provincial",
            "template_type": "training",
            "form_config": {
                "groups": [
                    {
                        "title": "项目基础信息",
                        "fields": [
                            {"key": "title", "label": "项目名称", "type": "text", "required": True, "system": True},
                            {"key": "project_type", "label": "项目类型", "type": "select", "required": True, "system": True, "options": [{"label": "创业训练", "value": "entrepreneurship_training"}, {"label": "创业实践", "value": "entrepreneurship_practice"}]},
                            {"key": "extra_info.duration", "label": "研究周期", "type": "select", "required": True, "options": [{"label": "1年", "value": "1"}, {"label": "2年", "value": "2"}]}
                        ]
                    },
                    {
                        "title": "指导教师信息",
                        "fields": []
                    },
                    {
                        "title": "核心内容",
                        "fields": [
                            {"key": "abstract", "label": "项目简介", "type": "richtext", "required": True, "system": True},
                            {"key": "extra_info.business_model", "label": "商业模式", "type": "richtext", "required": True},
                            {"key": "extra_info.expected_outcomes", "label": "预期成果", "type": "checkbox", "required": True, "options": [{"label": "商业计划书", "value": "business_plan"}, {"label": "公司注册", "value": "company_registration"}, {"label": "融资", "value": "financing"}, {"label": "营收", "value": "revenue"}]}
                        ]
                    },
                    {
                        "title": "财务与团队",
                        "fields": [
                            {"key": "extra_info.budget", "label": "经费预算", "type": "table", "required": True},
                            {"key": "members", "label": "团队成员", "type": "table", "required": True, "system": True, "columns": [{"label": "姓名", "key": "name", "width": 90}, {"label": "学号", "key": "student_id", "width": 120}, {"label": "年级", "key": "grade", "width": 90}, {"label": "专业", "key": "major", "width": 120}, {"label": "学院", "key": "college", "width": 120}, {"label": "联系方式", "key": "contact", "width": 140}]},
                            {"key": "extra_info.equity_structure", "label": "股权结构", "type": "table", "required": False}
                        ]
                    },
                    {
                        "title": "附件材料",
                        "fields": [
                            {"key": "extra_info.attachments.business_plan", "label": "商业计划书", "type": "file", "required": True, "placeholder": "PDF格式"},
                            {"key": "extra_info.attachments.business_license", "label": "营业执照", "type": "file", "required": False, "placeholder": "创业实践项目必填"}
                        ]
                    }
                ]
            }
        }
    },
    
    # ---- 三创赛体系 ----
    {
        "label": "三创赛（常规赛）",
        "value": "sanchuang_regular",
        "data": {
            "title": "全国大学生电子商务“创新、创意及创业”挑战赛（常规赛）",
            "system_type": "三创赛体系",
            "competition_level": "A类",
            "national_organizer": "教育部高校电子商务类专业教指委",
            "school_organizer": "创新创业学院",
            "level": "National",
            "template_type": "competition",
            "form_config": {
                "groups": [
                    {
                        "title": "项目基础信息",
                        "fields": [
                            {"key": "title", "label": "项目名称", "type": "text", "required": True, "system": True},
                            {"key": "extra_info.theme", "label": "参赛主题", "type": "select", "required": True, "options": [{"label": "三农电商", "value": "agriculture"}, {"label": "工业电商", "value": "industry"}, {"label": "跨境电商", "value": "cross_border"}, {"label": "电商物流", "value": "logistics"}, {"label": "互联网金融", "value": "finance"}, {"label": "移动电商", "value": "mobile"}, {"label": "旅游电商", "value": "tourism"}, {"label": "校园电商", "value": "campus"}, {"label": "其他类电商", "value": "other"}]}
                        ]
                    },
                    {
                        "title": "核心内容",
                        "fields": [
                            {"key": "extra_info.innovation", "label": "项目创新点", "type": "richtext", "required": True},
                            {"key": "extra_info.creativity", "label": "项目创意点", "type": "richtext", "required": True},
                            {"key": "extra_info.feasibility", "label": "项目可行性分析", "type": "richtext", "required": True},
                            {"key": "extra_info.business_model", "label": "商业模式设计", "type": "richtext", "required": True}
                        ]
                    },
                    {
                        "title": "团队信息",
                        "fields": [
                            {"key": "members", "label": "团队成员", "type": "table", "required": True, "system": True},
                            {"key": "advisor_name", "label": "指导教师", "type": "text", "required": True, "system": True}
                        ]
                    },
                    {
                        "title": "附件材料",
                        "fields": [
                            {"key": "extra_info.attachments.business_plan", "label": "商业计划书", "type": "file", "required": True, "placeholder": "PDF格式"},
                            {"key": "extra_info.attachments.pitch_deck", "label": "路演PPT", "type": "file", "required": True, "placeholder": "PPT/PPTX格式"}
                        ]
                    }
                ]
            }
        }
    },
    {
        "label": "三创赛（实战赛）",
        "value": "sanchuang_practical",
        "data": {
            "title": "全国大学生电子商务“创新、创意及创业”挑战赛（实战赛）",
            "system_type": "三创赛体系",
            "competition_level": "A类",
            "national_organizer": "教育部高校电子商务类专业教指委",
            "school_organizer": "相关学院",
            "level": "National",
            "template_type": "competition",
            "form_config": {
                "groups": [
                    {
                        "title": "项目基础信息",
                        "fields": [
                            {"key": "title", "label": "项目名称", "type": "text", "required": True, "system": True},
                            {"key": "extra_info.track", "label": "实战赛赛道", "type": "select", "required": True, "options": [{"label": "跨境电商", "value": "cross_border"}, {"label": "乡村振兴", "value": "rural_revitalization"}, {"label": "产学用(BUC)", "value": "buc"}, {"label": "商务大数据分析", "value": "big_data"}, {"label": "直播电商", "value": "live_streaming"}, {"label": "文旅电商", "value": "tourism"}, {"label": "AI电商", "value": "ai"}, {"label": "大健康电商", "value": "health"}, {"label": "美妆新零售", "value": "beauty"}]}
                        ]
                    },
                    {
                        "title": "核心内容",
                        "fields": [
                            {"key": "abstract", "label": "项目简介", "type": "richtext", "required": True, "system": True},
                            {"key": "extra_info.operation_strategy", "label": "运营策略", "type": "richtext", "required": True},
                            {"key": "extra_info.channels", "label": "运营平台/渠道", "type": "textarea", "required": True}
                        ]
                    },
                    {
                        "title": "团队信息",
                        "fields": [
                            {"key": "members", "label": "团队成员", "type": "table", "required": True, "system": True},
                            {"key": "advisor_name", "label": "指导教师", "type": "text", "required": True, "system": True}
                        ]
                    },
                    {
                        "title": "运营数据",
                        "fields": [
                            {"key": "extra_info.attachments.operation_data", "label": "运营数据证明", "type": "file", "required": True, "placeholder": "销售额截图、后台数据等"},
                            {"key": "extra_info.attachments.live_record", "label": "直播/运营记录", "type": "file", "required": False, "placeholder": "视频、截图"}
                        ]
                    },
                    {
                        "title": "附件材料",
                        "fields": [
                            {"key": "extra_info.attachments.consent_form", "label": "实战赛知情书", "type": "file", "required": True, "placeholder": "需签字"},
                            {"key": "extra_info.attachments.business_plan", "label": "商业计划书", "type": "file", "required": False, "placeholder": "PDF格式"}
                        ]
                    }
                ]
            }
        }
    }
]

with open('static/js/app.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if 'presetTemplates: [' in line:
        start_idx = i
        break

if start_idx != -1:
    bracket_count = 0
    in_block = False
    for i in range(start_idx, len(lines)):
        line = lines[i]
        for char in line:
            if char == '[':
                bracket_count += 1
                in_block = True
            elif char == ']':
                bracket_count -= 1
        if in_block and bracket_count == 0:
            end_idx = i
            break

if start_idx != -1 and end_idx != -1:
    # replace lines
    new_json = json.dumps(presets, indent=4, ensure_ascii=False)
    # indent properly
    indented_json = '\n'.join('            ' + l for l in new_json.split('\n'))
    
    new_lines = lines[:start_idx] + [f"            presetTemplates: {indented_json.strip()},\n"] + lines[end_idx+1:]
    
    with open('static/js/app.js', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print("Updated app.js successfully.")
else:
    print(f"Failed. start_idx={start_idx}, end_idx={end_idx}")
