const { createApp, ref, computed, onMounted } = Vue;
console.log('%c App.js Version: v27 Loaded ', 'background: #222; color: #bada55; font-size: 16px; padding: 4px;');
const { createRouter, createWebHashHistory } = VueRouter;

// --- GLOBAL AXIOS INTERCEPTOR ---
// Prevent any request to Ghost IDs (6, 7, 8, 9)
axios.interceptors.request.use(config => {
    if (config.url) {
        // Regex to match /projects/6, /projects/7, etc.
        // Matches /projects/9, /projects/9/audit, /projects/9/files, etc.
        const ghostPattern = /\/projects\/(6|7|8|9)(\/|$|\?)/;
        if (ghostPattern.test(config.url)) {
            const msg = `CRITICAL INTERCEPTOR: Blocked request to Ghost ID URL: ${config.url}`;
            console.error(msg);
            alert('系统安全拦截：检测到非法项目ID请求。请刷新页面。');
            return Promise.reject(new Error(msg));
        }
        
        // Also check body for ID 9 if it's a PUT/POST
        if (config.data && typeof config.data === 'object') {
             if ([6, 7, 8, 9].includes(Number(config.data.id))) {
                 const msg = `CRITICAL INTERCEPTOR: Blocked request with Ghost ID in body: ${config.data.id}`;
                 console.error(msg);
                 alert('系统安全拦截：检测到非法项目ID数据。请刷新页面。');
                 return Promise.reject(new Error(msg));
             }
        }
    }
    return config;
}, error => {
    return Promise.reject(error);
});

// --- 常量定义 ---
const ROLES = {
    SYSTEM_ADMIN: 'system_admin',
    PROJECT_ADMIN: 'project_admin',
    COLLEGE_APPROVER: 'college_approver',
    SCHOOL_APPROVER: 'school_approver',
    JUDGE: 'judge',
    TEACHER: 'teacher',
    STUDENT: 'student'
};

const STATUS_MAP = {
    'pending': { text: '待导师审核', type: 'warning' },
    'advisor_approved': { text: '待学院审批', type: 'primary' },
    'college_approved': { text: '待学校审批', type: 'primary' }, // Old status, might still be used
    'under_review': { text: '立项答辩评审中', type: 'warning' }, // New: College Approved -> Under Review
    'school_approved': { text: '待立项确认', type: 'info' }, // New meaning: Reviewed -> School Approved -> Rated
    'rated': { text: '已立项', type: 'success' },
    'rejected': { text: '已驳回', type: 'danger' },
    // 新增状态映射
    'midterm_submitted': { text: '中期-待导师审核', type: 'warning' },
    'midterm_advisor_approved': { text: '中期-待学院审核', type: 'primary' },
    'midterm_college_reviewing': { text: '中期-学院评审中', type: 'warning' }, // New
    'midterm_college_approved': { text: '中期-待学校审核', type: 'primary' },
    'midterm_approved': { text: '中期检查通过', type: 'success' },
    'midterm_rejected': { text: '中期-已驳回', type: 'danger' },
    'conclusion_submitted': { text: '结项-待导师审核', type: 'warning' },
    'conclusion_advisor_approved': { text: '结项-待学院审核', type: 'primary' },
    'conclusion_college_approved': { text: '结项-待学校审核', type: 'primary' },
    'under_final_review': { text: '结题评审中', type: 'warning' }, // New
    'finished': { text: '已结项', type: 'success' },
    'conclusion_rejected': { text: '结项-已驳回', type: 'danger' }
};

// --- 组件定义 ---

// 1. 登录组件 (移除注册功能，由管理员创建账号)
const Login = {
    template: `
    <div class="login-container">
        <el-card class="login-card">
            <template #header>
                <div class="card-header">
                    <h2>大创项目管理系统</h2>
                    <p class="subtitle">University Innovation & Entrepreneurship Platform</p>
                </div>
            </template>
            <el-form :model="form" label-position="top" size="large" class="login-form">
                <el-form-item label="用户名" required>
                    <el-input v-model="form.username" placeholder="请输入用户名" prefix-icon="User"></el-input>
                </el-form-item>
                <el-form-item label="密码" required>
                    <el-input v-model="form.password" type="password" placeholder="请输入密码" prefix-icon="Lock" show-password @keyup.enter="handleSubmit"></el-input>
                </el-form-item>
                
                <el-form-item>
                    <el-button type="primary" class="full-width-btn" style="width: 100%; font-weight: bold; height: 45px;" @click="handleSubmit" :loading="loading">
                        {{ isRegister ? '注册' : '立即登录' }}
                    </el-button>
                </el-form-item>

                <div v-if="!isRegister" class="mt-4" style="text-align: center;">
                    <p style="color: #909399; font-size: 13px; margin-bottom: 10px;">—— 快速测试通道 ——</p>
                    <div style="display:flex; gap:8px; flex-wrap:wrap; justify-content: center;">
                        <el-tag size="small" type="info" style="cursor: pointer;" @click="fillQuick('teacher')">老师</el-tag>
                        <el-tag size="small" type="info" style="cursor: pointer;" @click="fillQuick('student')">学生</el-tag>
                        <el-tag size="small" type="info" style="cursor: pointer;" @click="fillQuick('judge')">评审</el-tag>
                        <el-tag size="small" type="info" style="cursor: pointer;" @click="fillQuick('college')">学院</el-tag>
                        <el-tag size="small" type="info" style="cursor: pointer;" @click="fillQuick('school')">学校</el-tag>
                        <el-tag size="small" type="success" style="cursor: pointer;" @click="fillQuick('proj_admin')">项目管理</el-tag>
                        <el-tag size="small" type="danger" style="cursor: pointer;" @click="fillQuick('admin')">管理员</el-tag>
                    </div>
                </div>
                
                <div class="form-footer" style="text-align: center; margin-top: 20px;">
                    <el-link type="primary" @click="toggleMode" :underline="false">{{ isRegister ? '已有账号？去登录' : '注册新账号' }}</el-link>
                </div>
                
                <template v-if="isRegister">
                    <el-divider>注册信息</el-divider>
                    <el-form-item label="角色" required>
                        <el-select v-model="form.role" style="width: 100%">
                            <el-option label="学生" value="student"></el-option>
                            <el-option label="指导老师" value="teacher"></el-option>
                        </el-select>
                    </el-form-item>
                    <el-form-item label="真实姓名" required><el-input v-model="form.real_name"></el-input></el-form-item>
                    <el-form-item label="学号/工号" required><el-input v-model="form.identity_number"></el-input></el-form-item>
                    <el-form-item label="学院"><el-input v-model="form.college"></el-input></el-form-item>
                    <el-form-item label="系/专业"><el-input v-model="form.department"></el-input></el-form-item>
                </template>
            </el-form>
        </el-card>
    </div>
    `,
    data() {
        return {
            loading: false,
            isRegister: false,
            form: {
                username: '',
                password: '',
                role: 'student', // default for register
                real_name: '',
                college: '',
                department: '',
                identity_number: ''
            }
        }
    },
    methods: {
        toggleMode() {
            this.isRegister = !this.isRegister;
            this.form = { username: '', password: '', role: 'student', real_name: '', college: '', department: '', identity_number: '' };
        },
        async handleSubmit() {
            if (!this.form.username || !this.form.password) {
                ElementPlus.ElMessage.warning('请输入用户名和密码');
                return;
            }
            
            this.loading = true;
            try {
                if (this.isRegister) {
                    await axios.post('/api/register', this.form);
                    ElementPlus.ElMessage.success('注册申请已提交，请等待审核');
                    this.toggleMode();
                } else {
                    const res = await axios.post('/api/login', this.form);
                    ElementPlus.ElMessage.success('登录成功');
                    this.$emit('login-success', res.data.user);
                    this.$router.push('/');
                }
            } catch (error) {
                ElementPlus.ElMessage.error(error.response?.data?.error || '操作失败');
            } finally {
                this.loading = false;
            }
        },
        fillQuick(type) {
            const map = {
                admin: { u: 'admin', p: 'admin123' },
                teacher: { u: 'teacher1', p: 'teacher123' },
                student: { u: 'student1', p: 'student123' },
                judge: { u: 'judge1', p: 'admin123' },
                college: { u: 'col_approver', p: 'admin123' },
                school: { u: 'sch_approver', p: 'admin123' },
                proj_admin: { u: 'proj_admin', p: 'admin123' }
            };
            const v = map[type];
            if (v) { 
                this.form.username = v.u; 
                this.form.password = v.p; 
                ElementPlus.ElMessage.success('已自动填充测试账号: ' + v.u);
            }
        }
    }
};

const FIELD_LIBRARY = [
    { label: '项目名称', key: 'title', type: 'text', required: true, system: true, placeholder: '请输入项目名称' },
    { label: '项目类型', key: 'project_type', type: 'select', required: true, system: true, options: [], placeholder: '请选择项目类型' },
    { label: '研究周期', key: 'extra_info.duration', type: 'select', required: true, options: [{label:'1年',value:'1'}, {label:'2年',value:'2'}], placeholder: '请选择研究周期' },
    { label: '所属学科', key: 'extra_info.subject', type: 'select', required: true, options: [], placeholder: '请选择所属学科' },
    { label: '项目简介', key: 'abstract', type: 'richtext', required: true, system: true, placeholder: '请输入项目简介' },
    { label: '创新点描述', key: 'extra_info.innovation_points', type: 'richtext', required: true, placeholder: '请输入创新点描述' },
    { label: '预期成果', key: 'extra_info.expected_outcomes', type: 'checkbox', required: true, options: [{label:'论文',value:'paper'}, {label:'专利',value:'patent'}, {label:'软著',value:'software'}, {label:'实物',value:'product'}, {label:'调研报告',value:'report'}], placeholder: '请选择预期成果' },
    { label: '指导教师', key: 'advisor_name', type: 'text', required: true, system: true, placeholder: '请输入指导教师姓名' }, // Simplified for now
    { label: '团队成员', key: 'members', type: 'table', required: true, system: true, placeholder: '请添加团队成员' }, // Placeholder for table type support
    { label: '经费预算', key: 'extra_info.budget', type: 'table', required: true, placeholder: '请填写经费预算' },
    { label: '申报书附件', key: 'extra_info.attachments.application_doc', type: 'file', required: true, placeholder: '请上传申报书' },
    { label: '公司名称', key: 'extra_info.company_info.name', type: 'text', required: true, placeholder: '请输入公司名称' },
    { label: '统一社会信用代码', key: 'extra_info.company_info.code', type: 'text', required: false, placeholder: '请输入统一社会信用代码' },
    { label: '注册时间', key: 'extra_info.company_info.founded_date', type: 'date', required: false, placeholder: '请选择注册时间' },
    { label: '注册资本(万元)', key: 'extra_info.company_info.capital', type: 'number', required: false, placeholder: '请输入注册资本' },
    { label: '股权结构', key: 'extra_info.company_info.equity_structure', type: 'textarea', required: true, placeholder: '请描述股权结构' },
    { label: '所属行业', key: 'extra_info.industry', type: 'select', required: true, options: [], placeholder: '请选择所属行业' },
    { label: '入驻园区', key: 'extra_info.park', type: 'text', required: false, placeholder: '请输入入驻园区' },
    { label: '当前阶段', key: 'extra_info.stage', type: 'select', required: true, options: [{label:'创意',value:'idea'}, {label:'产品',value:'product'}, {label:'营收',value:'revenue'}, {label:'融资',value:'financing'}], placeholder: '请选择当前阶段' },
    { label: '融资记录', key: 'extra_info.company_info.investments', type: 'table', required: false, placeholder: '请填写融资记录' },
    { label: '商业计划书', key: 'extra_info.attachments.business_plan', type: 'file', required: true, placeholder: '请上传商业计划书' },
    { label: '营业执照', key: 'extra_info.attachments.license', type: 'file', required: false, placeholder: '请上传营业执照' },
    { label: '参赛赛道', key: 'extra_info.track', type: 'select', required: true, options: [{label:'高教主赛道',value:'main'}, {label:'红旅赛道',value:'red'}, {label:'产业命题赛道',value:'industry'}], placeholder: '请选择参赛赛道' },
    { label: '参赛组别', key: 'extra_info.group', type: 'select', required: true, options: [{label:'本科生创意组',value:'undergrad_idea'}, {label:'研究生创意组',value:'grad_idea'}, {label:'创业组',value:'startup'}, {label:'公益组',value:'charity'}], placeholder: '请选择参赛组别' },
    { label: '行业痛点', key: 'extra_info.pain_points', type: 'textarea', required: true, placeholder: '请输入行业痛点' },
    { label: '商业模式', key: 'extra_info.business_model', type: 'richtext', required: true, placeholder: '请输入商业模式' },
    { label: '竞品分析', key: 'extra_info.competitor_analysis', type: 'richtext', required: false, placeholder: '请输入竞品分析' },
    { label: '路演PPT', key: 'extra_info.attachments.pitch_deck', type: 'file', required: true, placeholder: '请上传路演PPT' },
    { label: '1分钟视频', key: 'extra_info.attachments.video', type: 'file', required: false, placeholder: '请上传1分钟视频' },
    { label: '获奖情况', key: 'extra_info.awards', type: 'table', required: false, placeholder: '请填写获奖情况' },
    { label: '作品类别', key: 'extra_info.work_category', type: 'select', required: true, options: [{label:'自然科学类学术论文',value:'science_paper'}, {label:'哲学社会科学类社会调查报告',value:'social_report'}, {label:'科技发明制作',value:'tech_invention'}], placeholder: '请选择作品类别' },
    { label: '研究背景', key: 'extra_info.research_background', type: 'richtext', required: true, placeholder: '请输入研究背景' },
    { label: '研究方法', key: 'extra_info.research_method', type: 'textarea', required: true, placeholder: '请输入研究方法' },
    { label: '应用价值', key: 'extra_info.application_value', type: 'textarea', required: false, placeholder: '请输入应用价值' },
    { label: '论文/报告全文', key: 'extra_info.attachments.full_paper', type: 'file', required: true, placeholder: '请上传论文/报告全文' },
    { label: '查重报告', key: 'extra_info.attachments.plagiarism_report', type: 'file', required: true, placeholder: '请上传查重报告' },
    { label: '支撑材料', key: 'extra_info.attachments.supporting_materials', type: 'file', required: false, placeholder: '请上传支撑材料' },
    { label: '目标客户', key: 'extra_info.target_customers', type: 'textarea', required: true, placeholder: '请输入目标客户' },
    { label: '竞争优势', key: 'extra_info.competitive_advantage', type: 'textarea', required: true, placeholder: '请输入竞争优势' },
    { label: '累计融资金额(万元)', key: 'extra_info.total_funding', type: 'number', required: false, placeholder: '请输入累计融资金额' },
    { label: '产品演示', key: 'extra_info.attachments.product_demo', type: 'file', required: false, placeholder: '请上传产品演示' }
];

const FormDesigner = {
    name: 'FormDesigner',
    props: {
        modelValue: {
            type: Object,
            default: () => ({ groups: [] })
        }
    },
    emits: ['update:modelValue'],
    data() {
        return {
            config: { groups: [] },
            showFieldDialog: false,
            showLibraryDialog: false,
            currentGroupIndex: -1,
            currentFieldIndex: -1,
            fieldLibrary: FIELD_LIBRARY,
            editingField: {
                key: '',
                label: '',
                type: 'text',
                required: false,
                system: false,
                placeholder: '',
                default_value: '',
                options: [],
                validation: {}
            },
            fieldTypes: [
                { label: '单行文本', value: 'text' },
                { label: '多行文本', value: 'textarea' },
                { label: '下拉选择', value: 'select' },
                { label: '单选按钮', value: 'radio' },
                { label: '多选框', value: 'checkbox' },
                { label: '日期选择', value: 'date' },
                { label: '数字输入', value: 'number' },
                { label: '文件上传', value: 'file' },
                { label: '富文本', value: 'richtext' },
                { label: '表格', value: 'table' } // Added table support
            ],
            history: [],
            historyIndex: -1,
            isUndoRedo: false
        };
    },
    watch: {
        modelValue: {
            handler(val) {
                if (this.isUndoRedo) {
                    this.isUndoRedo = false;
                    return;
                }
                if (val && val.groups) {
                    this.config = JSON.parse(JSON.stringify(val));
                    this.recordHistory();
                } else {
                    this.config = { groups: [] };
                    this.recordHistory();
                }
            },
            immediate: true,
            deep: true
        }
    },
    methods: {
        // --- History Management ---
        recordHistory() {
            // Remove future history if we are in the middle
            if (this.historyIndex < this.history.length - 1) {
                this.history = this.history.slice(0, this.historyIndex + 1);
            }
            this.history.push(JSON.parse(JSON.stringify(this.config)));
            this.historyIndex = this.history.length - 1;
        },
        undo() {
            if (this.historyIndex > 0) {
                this.historyIndex--;
                this.isUndoRedo = true;
                this.config = JSON.parse(JSON.stringify(this.history[this.historyIndex]));
                this.emitUpdate();
            }
        },
        redo() {
            if (this.historyIndex < this.history.length - 1) {
                this.historyIndex++;
                this.isUndoRedo = true;
                this.config = JSON.parse(JSON.stringify(this.history[this.historyIndex]));
                this.emitUpdate();
            }
        },
        reset() {
            // Reset to the very first history state
            if (this.history.length > 0) {
                // If historyIndex is 0, we are already at the beginning of history.
                // However, user might want to reset to the "preset" state if they loaded a preset.
                // The history[0] is the state when the designer was MOUNTED or prop updated.
                // If v-if destroyed the component, history starts fresh with the current prop value.
                
                this.historyIndex = 0;
                this.isUndoRedo = true;
                this.config = JSON.parse(JSON.stringify(this.history[0]));
                this.emitUpdate();
                
                // Clear future history? No, user might want to "Undo" the reset.
                // We treat "Reset" as a new action that restores state 0.
                this.recordHistory();
            }
        },

        // --- Group Management ---
        addGroup() {
            this.config.groups.push({
                title: '新分组',
                fields: []
            });
            this.emitUpdate();
        },
        removeGroup(index) {
            this.config.groups.splice(index, 1);
            this.emitUpdate();
        },
        moveGroup(index, direction) {
            if (direction === -1 && index > 0) {
                const temp = this.config.groups[index];
                this.config.groups[index] = this.config.groups[index - 1];
                this.config.groups[index - 1] = temp;
            } else if (direction === 1 && index < this.config.groups.length - 1) {
                const temp = this.config.groups[index];
                this.config.groups[index] = this.config.groups[index + 1];
                this.config.groups[index + 1] = temp;
            }
            this.emitUpdate();
        },

        // --- Field Management ---
        addField(groupIndex) {
            this.currentGroupIndex = groupIndex;
            this.showLibraryDialog = true;
        },
        addCustomField() {
            this.showLibraryDialog = false;
            this.currentFieldIndex = -1; // New field
            this.editingField = {
                key: 'field_' + Date.now(),
                label: '新字段',
                type: 'text',
                required: false,
                system: false,
                options: []
            };
            this.showFieldDialog = true;
        },
        addFieldFromLib(fieldTemplate) {
            this.config.groups[this.currentGroupIndex].fields.push(JSON.parse(JSON.stringify(fieldTemplate)));
            this.showLibraryDialog = false;
            this.emitUpdate();
            ElementPlus.ElMessage.success('已添加字段：' + fieldTemplate.label);
        },
        editField(groupIndex, fieldIndex) {
            this.currentGroupIndex = groupIndex;
            this.currentFieldIndex = fieldIndex;
            this.editingField = JSON.parse(JSON.stringify(this.config.groups[groupIndex].fields[fieldIndex]));
            if (!this.editingField.options) this.editingField.options = [];
            this.showFieldDialog = true;
        },
        removeField(groupIndex, fieldIndex) {
            const field = this.config.groups[groupIndex].fields[fieldIndex];
            if (field.system) {
                // Allow removing system fields from the form view
            }
            this.config.groups[groupIndex].fields.splice(fieldIndex, 1);
            this.emitUpdate();
        },
        moveField(groupIndex, fieldIndex, direction) {
            const fields = this.config.groups[groupIndex].fields;
            if (direction === -1 && fieldIndex > 0) {
                const temp = fields[fieldIndex];
                fields[fieldIndex] = fields[fieldIndex - 1];
                fields[fieldIndex - 1] = temp;
            } else if (direction === 1 && fieldIndex < fields.length - 1) {
                const temp = fields[fieldIndex];
                fields[fieldIndex] = fields[fieldIndex + 1];
                fields[fieldIndex + 1] = temp;
            }
            this.emitUpdate();
        },

        // --- Edit Dialog ---
        saveField() {
            if (!this.editingField.label) {
                ElementPlus.ElMessage.warning('请输入字段标签');
                return;
            }
            if (!this.editingField.key) {
                ElementPlus.ElMessage.warning('请输入字段标识');
                return;
            }

            if (this.currentFieldIndex === -1) {
                // Add new
                this.config.groups[this.currentGroupIndex].fields.push(this.editingField);
            } else {
                // Update existing
                this.config.groups[this.currentGroupIndex].fields.splice(this.currentFieldIndex, 1, this.editingField);
            }
            this.showFieldDialog = false;
            this.emitUpdate();
        },
        addOption() {
            this.editingField.options.push({ label: '新选项', value: 'opt_' + Date.now() });
        },
        removeOption(index) {
            this.editingField.options.splice(index, 1);
        },

        emitUpdate() {
            this.$emit('update:modelValue', this.config);
        }
    },
    template: `
    <div class="form-designer">
        <div class="toolbar" style="margin-bottom: 15px; display: flex; justify-content: space-between;">
            <div>
                <el-button type="primary" size="small" @click="addGroup">➕ 添加分组</el-button>
            </div>
            <div>
                <el-tooltip content="撤销 (Undo)" placement="top">
                    <el-button size="small" circle icon="RefreshLeft" @click="undo" :disabled="historyIndex <= 0"></el-button>
                </el-tooltip>
                <el-tooltip content="重做 (Redo)" placement="top">
                    <el-button size="small" circle icon="RefreshRight" @click="redo" :disabled="historyIndex >= history.length - 1"></el-button>
                </el-tooltip>
                <el-divider direction="vertical"></el-divider>
                <el-button size="small" type="warning" plain @click="reset">↺ 重置初始状态</el-button>
            </div>
        </div>

        <div v-for="(group, gIndex) in config.groups" :key="gIndex" class="designer-group" style="border: 1px solid #dcdfe6; margin-bottom: 15px; padding: 10px; border-radius: 4px;">
            <div class="group-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; background: #f5f7fa; padding: 5px;">
                <div style="font-weight: bold;">
                    <el-input v-model="group.title" size="small" style="width: 200px;" placeholder="分组标题"></el-input>
                </div>
                <div>
                    <el-button size="small" circle icon="ArrowUp" @click="moveGroup(gIndex, -1)" :disabled="gIndex === 0"></el-button>
                    <el-button size="small" circle icon="ArrowDown" @click="moveGroup(gIndex, 1)" :disabled="gIndex === config.groups.length - 1"></el-button>
                    <el-button type="danger" size="small" circle icon="Delete" @click="removeGroup(gIndex)"></el-button>
                </div>
            </div>

            <div class="field-list">
                <div v-for="(field, fIndex) in group.fields" :key="fIndex" class="designer-field" style="display: flex; justify-content: space-between; align-items: center; padding: 8px; border-bottom: 1px dashed #eee;">
                    <div class="field-info">
                        <span style="margin-right: 10px; font-weight: 500;">{{ field.label }}</span>
                        <el-tag size="small" type="info">{{ fieldTypes.find(t => t.value === field.type)?.label || field.type }}</el-tag>
                        <el-tag v-if="field.required" size="small" type="danger" style="margin-left: 5px;">必填</el-tag>
                        <el-tag v-if="field.system" size="small" type="warning" style="margin-left: 5px;">系统</el-tag>
                    </div>
                    <div class="field-actions">
                        <el-button size="small" circle icon="ArrowUp" @click="moveField(gIndex, fIndex, -1)" :disabled="fIndex === 0"></el-button>
                        <el-button size="small" circle icon="ArrowDown" @click="moveField(gIndex, fIndex, 1)" :disabled="fIndex === group.fields.length - 1"></el-button>
                        <el-button size="small" circle icon="Edit" @click="editField(gIndex, fIndex)"></el-button>
                        <el-button size="small" circle icon="Delete" type="danger" @click="removeField(gIndex, fIndex)" :disabled="field.system"></el-button>
                    </div>
                </div>
                <div style="text-align: center; margin-top: 10px;">
                    <el-button size="small" style="width: 100%; border-style: dashed;" @click="addField(gIndex)">+ 添加字段</el-button>
                </div>
            </div>
        </div>

        <!-- Library Dialog -->
        <el-dialog v-model="showLibraryDialog" title="选择字段" width="600px" append-to-body>
            <div style="display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px;">
                <el-button v-for="field in fieldLibrary" :key="field.key" size="small" @click="addFieldFromLib(field)">
                    {{ field.label }}
                </el-button>
            </div>
            <el-divider>或</el-divider>
            <div style="text-align: center;">
                <el-button type="primary" @click="addCustomField">新建自定义字段</el-button>
            </div>
        </el-dialog>

        <!-- Field Configuration Dialog -->
        <el-dialog v-model="showFieldDialog" title="字段配置" width="600px" append-to-body>
            <el-form :model="editingField" label-width="100px">
                <el-tabs type="border-card">
                    <el-tab-pane label="基础设置">
                        <el-form-item label="字段类型">
                            <el-select v-model="editingField.type" :disabled="editingField.system">
                                <el-option v-for="t in fieldTypes" :key="t.value" :label="t.label" :value="t.value"></el-option>
                            </el-select>
                        </el-form-item>
                        <el-form-item label="字段标识">
                            <el-input v-model="editingField.key" :disabled="editingField.system" placeholder="如: project_name"></el-input>
                            <div v-if="editingField.system" style="font-size: 12px; color: #e6a23c;">系统字段无法修改标识</div>
                        </el-form-item>
                        <el-form-item label="字段标签">
                            <el-input v-model="editingField.label" placeholder="如: 项目名称"></el-input>
                        </el-form-item>
                        <el-form-item label="提示文字">
                            <el-input v-model="editingField.placeholder" placeholder="输入框内的提示"></el-input>
                        </el-form-item>
                        <el-form-item label="是否必填">
                            <el-switch v-model="editingField.required"></el-switch>
                        </el-form-item>
                    </el-tab-pane>
                    
                    <el-tab-pane label="高级选项" v-if="['select', 'radio', 'checkbox'].includes(editingField.type)">
                        <div v-for="(opt, idx) in editingField.options" :key="idx" style="display: flex; gap: 10px; margin-bottom: 10px;">
                            <el-input v-model="opt.label" placeholder="选项名"></el-input>
                            <el-input v-model="opt.value" placeholder="选项值"></el-input>
                            <el-button type="danger" circle icon="Delete" @click="removeOption(idx)"></el-button>
                        </div>
                        <el-button size="small" @click="addOption">+ 添加选项</el-button>
                    </el-tab-pane>
                    
                    <el-tab-pane label="校验规则">
                        <!-- Simplified validation for now -->
                        <el-form-item label="正则(可选)">
                            <el-input v-model="editingField.validation.regex" placeholder="/^...$/"></el-input>
                        </el-form-item>
                        <el-form-item label="错误提示">
                            <el-input v-model="editingField.validation.message" placeholder="校验失败时的提示"></el-input>
                        </el-form-item>
                    </el-tab-pane>
                </el-tabs>
            </el-form>
            <template #footer>
                <el-button @click="showFieldDialog = false">取消</el-button>
                <el-button type="primary" @click="saveField">确定</el-button>
            </template>
        </el-dialog>
    </div>
    `
};

// 2. Dashboard 组件
const Dashboard = {
    template: `
    <div class="dashboard-container">
        <!-- 欢迎栏 -->
        <el-alert v-if="user" :title="'欢迎回来，' + user.real_name" type="success" :closable="false" class="mb-4">
            <template #default>
                您的角色: {{ getRoleName(user?.role) }} | {{ user?.college ? user.college : '校级管理' }}
            </template>
        </el-alert>

        <el-alert 
            v-if="user?.role === 'student' && missingPitchProjectsCount > 0" 
            :title="'提示：您有 ' + missingPitchProjectsCount + ' 个项目已进入评审阶段，请点击“上传路演材料”进入详细信息上传相关材料'" 
            type="warning" 
            :closable="false" 
            class="mb-4">
            <template #default>
                请尽快完成上传以便参与评审。
            </template>
        </el-alert>

        <!-- 公告栏 -->
        <el-card class="mb-4" shadow="hover">
            <template #header>
                <div class="card-header" style="display: flex; justify-content: space-between; align-items: center;">
                    <span><el-icon><Bell /></el-icon> 公告与新闻</span>
                    <el-button v-if="canManageSystem" type="primary" size="small" @click="showAnnouncementDialog = true">发布公告</el-button>
                </div>
            </template>
            <div v-if="announcements.length === 0" style="color: #999; text-align: center;">暂无公告</div>
            <div v-else v-for="anno in announcements" :key="anno.id" class="announcement-item" style="border-bottom: 1px solid #eee; padding: 10px 0;">
                <div style="display: flex; justify-content: space-between;">
                    <span style="font-weight: bold;">[{{ anno.type === 'news' ? '新闻' : '通知' }}] {{ anno.title }}</span>
                    <span style="font-size: 12px; color: #999;">{{ anno.created_at }}</span>
                </div>
                <div style="margin-top: 5px; color: #666;">{{ anno.content }}</div>
                <div v-if="canManageSystem" style="text-align: right; margin-top: 5px;">
                    <el-button type="danger" link size="small" @click="deleteAnnouncement(anno.id)">删除</el-button>
                </div>
            </div>
        </el-card>

        <el-tabs v-model="activeTab" class="dashboard-tabs" @tab-change="handleTabChange">
                <el-tab-pane label="个人中心" name="profile">
                    <el-row :gutter="20">
                        <el-col :span="12">
                            <el-card shadow="hover" header="基本信息">
                                <el-form label-width="100px" :model="profileForm">
                                    <el-form-item label="用户名">
                                        <el-input v-model="profileForm.username" disabled></el-input>
                                    </el-form-item>
                                    <el-form-item label="真实姓名">
                                        <el-input v-model="profileForm.real_name"></el-input>
                                    </el-form-item>
                                    <el-form-item label="角色">
                                        <el-tag>{{ getRoleName(profileForm.role) }}</el-tag>
                                    </el-form-item>
                                    <el-form-item label="学院">
                                        <el-input v-model="profileForm.college" :disabled="user?.role === 'student'"></el-input>
                                    </el-form-item>
                                    <el-form-item label="专业/部门">
                                        <el-input v-model="profileForm.department"></el-input>
                                    </el-form-item>
                                    <el-form-item label="联系电话">
                                        <el-input v-model="profileForm.phone"></el-input>
                                    </el-form-item>
                                    <el-form-item label="电子邮箱">
                                        <el-input v-model="profileForm.email"></el-input>
                                    </el-form-item>
                                    <el-form-item label="个人简介">
                                        <el-input type="textarea" v-model="profileForm.personal_info" :rows="3"></el-input>
                                    </el-form-item>
                                    <el-form-item>
                                        <el-button type="primary" @click="updateProfile" :loading="savingProfile">保存修改</el-button>
                                    </el-form-item>
                                </el-form>
                            </el-card>
                        </el-col>
                        <el-col :span="12">
                            <el-card shadow="hover" header="安全设置">
                                <el-form label-width="100px" :model="passwordForm">
                                    <el-form-item label="旧密码">
                                        <el-input v-model="passwordForm.old_password" type="password" show-password></el-input>
                                    </el-form-item>
                                    <el-form-item label="新密码">
                                        <el-input v-model="passwordForm.new_password" type="password" show-password></el-input>
                                    </el-form-item>
                                    <el-form-item label="确认新密码">
                                        <el-input v-model="passwordForm.confirm_password" type="password" show-password></el-input>
                                    </el-form-item>
                                    <el-form-item>
                                        <el-button type="warning" @click="updatePassword" :loading="changingPassword">修改密码</el-button>
                                    </el-form-item>
                                </el-form>
                            </el-card>
                        </el-col>
                    </el-row>
                </el-tab-pane>

                <el-tab-pane label="项目管理" name="projects">
                    <div class="filter-bar" style="display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap;">
                        <el-input v-model="filters.keyword" placeholder="搜索项目/负责人" style="width: 200px;" prefix-icon="Search" clearable></el-input>
                        
                        <el-select v-model="filters.year" placeholder="年份" clearable style="width: 100px">
                            <el-option label="2025" value="2025"></el-option>
                            <el-option label="2024" value="2024"></el-option>
                            <el-option label="2023" value="2023"></el-option>
                        </el-select>
                        <el-select v-model="filters.status" placeholder="状态" clearable style="width: 140px">
                            <el-option label="待审核" value="pending_audit"></el-option>
                            <el-option label="已通过" value="approved"></el-option>
                            <el-option label="已驳回" value="rejected"></el-option>
                        </el-select>
                        <el-select v-model="filters.type" placeholder="类型" clearable style="width: 140px">
                            <el-option label="创新训练" value="innovation"></el-option>
                            <el-option label="创业训练" value="entrepreneurship_training"></el-option>
                            <el-option label="创业实践" value="entrepreneurship_practice"></el-option>
                        </el-select>

                        <!-- Level Filter for Admins and Approvers -->
                        <el-select v-if="user?.role && ['system_admin', 'project_admin', 'school_approver', 'college_approver'].includes(user.role)" v-model="filters.level" placeholder="级别" clearable style="width: 100px">
                            <el-option label="校级" value="school"></el-option>
                            <el-option label="省级" value="provincial"></el-option>
                            <el-option label="国家级" value="national"></el-option>
                        </el-select>

                        <!-- 学生才有申请项目按钮 -->
                        <el-button v-if="user?.role === 'student'" type="primary" @click="openCreateDialog">申请项目</el-button>
                        
                        <!-- 审批人员操作 -->
                        <el-button-group v-if="user?.role && ['system_admin', 'project_admin', 'school_approver', 'college_approver'].includes(user.role)">
                             <el-button type="success" icon="Download" @click="exportProjects">导出</el-button>
                             <el-button type="info" icon="DataLine" @click="showStatsDialog = true">统计</el-button>
                        </el-button-group>
                    </div>
                    
                    <div style="margin-bottom: 10px; color: #999; font-size: 12px;">DEBUG: Projects Loaded: {{ projects.length }} | Filtered: {{ filteredProjects.length }}</div>
                    <el-table :data="filteredProjects" style="width: 100%" v-loading="loading">
                        <el-table-column prop="id" label="ID" width="50"></el-table-column>
                        <el-table-column prop="title" label="项目名称"></el-table-column>
                        <el-table-column prop="project_type" label="类型" width="100"></el-table-column>
                        <el-table-column prop="level" label="级别" width="100"></el-table-column>
                        <el-table-column prop="leader_name" label="负责人" width="100"></el-table-column>
                        <el-table-column label="商业计划书" width="140">
                            <template #default="scope">
                                <template v-if="scope.row.extra_info && scope.row.extra_info.attachments && scope.row.extra_info.attachments.business_plan">
                                    <el-link :href="scope.row.extra_info.attachments.business_plan" target="_blank" type="primary">查看/下载</el-link>
                                </template>
                                <span v-else style="color:#999">未上传</span>
                            </template>
                        </el-table-column>
                        <el-table-column label="状态" width="160">
                            <template #default="scope">
                                <el-tag :type="getStatusType(scope.row.status)">{{ getStatusTextForRow(scope.row) }}</el-tag>
                            </template>
                        </el-table-column>
                        <el-table-column label="操作" width="250" fixed="right">
                            <template #default="scope">
                                <el-button size="small" @click="viewDetails(scope.row.id)">详情</el-button>
                                
                                <!-- 导师审批 -->
                                <template v-if="canUserAudit(scope.row)">
                                    <el-button size="small" type="success" @click="openAuditDialog(scope.row, 'approve')">通过</el-button>
                                    <el-button size="small" type="danger" @click="openAuditDialog(scope.row, 'reject')">驳回</el-button>
                                </template>

                                <!-- 学院审批 -->
                                <template v-if="canUserAudit(scope.row)">
                                    <el-button size="small" type="success" @click="openAuditDialog(scope.row, 'approve')">学院通过</el-button>
                                    <el-button size="small" type="danger" @click="openAuditDialog(scope.row, 'reject')">学院驳回</el-button>
                                </template>

                                <!-- 学校审批 -->
                                <template v-if="canUserAudit(scope.row)">
                                    <el-button size="small" type="success" @click="openAuditDialog(scope.row, 'approve')">学校通过</el-button>
                                    <el-button size="small" type="danger" @click="openAuditDialog(scope.row, 'reject')">学校驳回</el-button>
                                </template>

                                <!-- Assign Reviewer Button for Admins -->
                                <template v-if="(user?.role === 'college_approver' && ['under_review', 'midterm_college_reviewing'].includes(scope.row.status)) || (user?.role === 'school_approver' && scope.row.status === 'under_final_review')">
                                     <el-button size="small" type="warning" @click="openAssignDialog(scope.row)">分配评委</el-button>
                                </template>

                                <!-- 评委评分 -->
                                <template v-if="canReview(scope.row)">
                                    <el-button size="small" type="warning" @click="openReviewDialog(scope.row)">评审</el-button>
                                </template>

                                <!-- 文件审核 - 快捷操作 -->
                                <template v-if="canFileAudit(scope.row)">
                                    <el-button size="small" type="primary" @click="viewDetails(scope.row.id)">审核材料</el-button>
                                </template>



                                <!-- 学生/负责人提交报告 -->
                                <template v-if="canUploadFile(scope.row)">
                                    <el-button size="small" type="primary" @click="openUploadDialogWithProject(scope.row)">提交材料</el-button>
                                </template>
                                
                                <!-- 学生上传路演材料（评审阶段） -->
                                <template v-if="user?.role === 'student' && scope.row.status === 'school_approved'">
                                    <el-button size="small" type="primary" @click="openPitchUploadWithProject(scope.row)">上传路演材料</el-button>
                                </template>
                                
                                <!-- 学生重报/修改 -->
                                <template v-if="user?.role === 'student' && (scope.row.status === 'rejected' || scope.row.status === 'pending' || scope.row.status === 'advisor_approved' || scope.row.status === 'college_approved')">
                                     <el-button size="small" type="warning" :disabled="!scope.row || !scope.row.id" @click="editProject(scope.row)">
                                         {{ scope.row.status === 'rejected' ? '修改重报' : '修改' }}
                                     </el-button>
                                 </template>

                                <!-- 管理员/审批者修改 -->
                                <template v-if="['college_approver', 'school_approver', 'project_admin'].includes(user?.role)">
                                     <el-button size="small" type="warning" :disabled="!scope.row || !scope.row.id" @click="editProject(scope.row)">修改</el-button>
                                </template>
                                
                                <!-- 管理员删除 -->
                                <template v-if="canManageSystem">
                                    <el-button size="small" type="danger" @click="deleteProject(scope.row)">删除</el-button>
                                </template>
                            </template>
                        </el-table-column>
                    </el-table>
            </el-tab-pane>

                <!-- Legacy Library Tab -->
                <el-tab-pane label="往届项目经验库" name="legacy">
                    <div class="filter-bar" style="display: flex; gap: 10px; margin-bottom: 20px;">
                        <el-input v-model="legacyKeyword" placeholder="搜索项目名称/方法论" style="width: 300px;" prefix-icon="Search" clearable @change="fetchLegacyProjects"></el-input>
                        <el-button type="primary" @click="fetchLegacyProjects">搜索</el-button>
                    </div>
                    <el-table :data="legacyProjects" style="width: 100%" stripe>
                         <el-table-column prop="title" label="项目名称"></el-table-column>
                         <el-table-column prop="methodology_summary" label="方法论总结" show-overflow-tooltip></el-table-column>
                         <el-table-column prop="expert_comments" label="专家评语(脱敏)" show-overflow-tooltip></el-table-column>
                         <el-table-column prop="borrowed_count" label="被借鉴次数" width="120" align="center"></el-table-column>
                         <el-table-column prop="created_at" label="收录时间" width="180"></el-table-column>
                         <el-table-column label="操作" width="120">
                             <template #default="scope">
                                 <el-link v-if="scope.row.ppt_url" :href="scope.row.ppt_url" target="_blank" type="primary">查看PPT</el-link>
                                 <span v-else>无PPT</span>
                             </template>
                         </el-table-column>
                    </el-table>
                </el-tab-pane>

            <el-tab-pane label="统计报表" name="reports" v-if="canViewReports">
                <div class="report-controls" style="margin-bottom: 20px;">
                    <el-button type="primary" @click="downloadReport" :loading="exporting">
                        <el-icon><Download /></el-icon> 导出项目报表 (CSV)
                    </el-button>
                    <el-button @click="fetchStats">刷新数据</el-button>
                </div>
                
                <div class="stats-charts" v-loading="loadingStats">
                    <el-row :gutter="20">
                        <el-col :span="12">
                            <el-card shadow="hover" header="项目状态分布">
                                <div ref="chartStatus" style="width: 100%; height: 300px;"></div>
                            </el-card>
                        </el-col>
                        <el-col :span="12">
                            <el-card shadow="hover" header="项目类型分布">
                                <div ref="chartType" style="width: 100%; height: 300px;"></div>
                            </el-card>
                        </el-col>
                    </el-row>
                    <el-row :gutter="20" style="margin-top: 20px;">
                        <el-col :span="24">
                            <el-card shadow="hover" header="各学院项目申报数量">
                                <div ref="chartCollege" style="width: 100%; height: 350px;"></div>
                            </el-card>
                        </el-col>
                    </el-row>
                </div>
            </el-tab-pane>

                <!-- 赛事大厅/可选项目 (学生可见) -->
                <el-tab-pane v-if="user?.role === 'student'" label="项目申报大厅" name="competitions">
                     <div class="filter-bar">
                         <h3>可选申报批次</h3>
                     </div>
                     <el-table :data="competitions" style="width: 100%" v-loading="loading">
                         <el-table-column prop="id" label="ID" width="60"></el-table-column>
                         <el-table-column prop="title" label="批次名称" min-width="200">
                             <template #default="scope">
                                 <strong>{{ scope.row.title }}</strong>
                                 <el-tag v-if="scope.row.form_config && scope.row.form_config.batch_type === 'program'" size="small" type="success" style="margin-left: 5px">常规项目</el-tag>
                                 <el-tag v-else-if="scope.row.form_config && scope.row.form_config.batch_type === 'competition'" size="small" type="warning" style="margin-left: 5px">学科竞赛</el-tag>
                                 <el-tag v-if="scope.row.level" size="small" style="margin-left: 5px;">{{ scope.row.level }}</el-tag>
                             </template>
                         </el-table-column>
                         <el-table-column prop="organizer" label="承办单位" width="150"></el-table-column>
                         <el-table-column label="报名时间" width="200">
                             <template #default="scope">
                                 {{ scope.row.registration_start }} 至 {{ scope.row.registration_end }}
                             </template>
                         </el-table-column>
                         <el-table-column label="状态" width="100">
                             <template #default="scope">
                                 <el-tag :type="scope.row.status === 'active' ? 'success' : 'info'">
                                     {{ scope.row.status === 'active' ? '进行中' : (scope.row.status === 'upcoming' ? '未开始' : '已结束') }}
                                 </el-tag>
                             </template>
                         </el-table-column>
                         <el-table-column label="操作" width="180" fixed="right">
                            <template #default="scope">
                                <template v-if="scope.row.is_registered">
                                    <el-button 
                                        v-if="['pending', 'rejected'].includes(scope.row.project_status)" 
                                        type="warning" 
                                        size="small"
                                        :disabled="!scope.row.project_id || Number(scope.row.project_id) <= 0 || [6, 7, 8, 9].includes(Number(scope.row.project_id))"
                                        @click="editProject({id: scope.row.project_id})">
                                        修改报名
                                    </el-button>
                                    <el-button 
                                        v-else 
                                        type="info" 
                                        size="small"
                                        :disabled="!scope.row.project_id || Number(scope.row.project_id) <= 0"
                                        @click="viewDetails(scope.row.project_id)">
                                        查看报名
                                    </el-button>
                                </template>
                                <el-button v-else-if="scope.row.status === 'active'" type="primary" size="small" @click="applyCompetition(scope.row)">
                                    {{ (scope.row.form_config && scope.row.form_config.batch_type === 'program') ? '申报项目' : '报名参赛' }}
                                </el-button>
                                <el-button v-else size="small" disabled>不可报名</el-button>
                            </template>
                        </el-table-column>
                     </el-table>
                </el-tab-pane>

                <!-- 赛事管理 (管理员可见) -->
                <el-tab-pane v-if="canManageSystem" label="申报批次管理" name="comp_mgmt">
                     <div class="filter-bar">
                         <el-button type="primary" @click="openCompDialog()">发布申报批次</el-button>
                     </div>
                     <el-table :data="competitions" style="width: 100%" v-loading="loading">
                        <el-table-column prop="id" label="ID" width="60"></el-table-column>
                        <el-table-column prop="title" label="批次名称">
                             <template #default="scope">
                                 <span>{{ scope.row.title }}</span>
                                 <el-tag v-if="scope.row.form_config && scope.row.form_config.batch_type === 'program'" size="small" type="success" style="margin-left: 5px">常规项目</el-tag>
                                 <el-tag v-else-if="scope.row.form_config && scope.row.form_config.batch_type === 'competition'" size="small" type="warning" style="margin-left: 5px">学科竞赛</el-tag>
                             </template>
                        </el-table-column>
                        <el-table-column prop="level" label="级别"></el-table-column>
                        <el-table-column prop="status" label="状态"></el-table-column>
                        <el-table-column prop="template_type" label="模板类型">
                            <template #default="scope">
                                {{ scope.row.template_type === 'startup' ? '创业组(Template 2)' : '默认(Template 1)' }}
                            </template>
                        </el-table-column>
                        <el-table-column label="操作">
                            <template #default="scope">
                                <el-button size="small" @click="openCompDialog(scope.row)">编辑</el-button>
                                <el-button size="small" type="danger" @click="deleteCompetition(scope.row.id)">删除</el-button>
                            </template>
                        </el-table-column>
                    </el-table>
               </el-tab-pane>

            <!-- 2. 用户管理 (管理员可见) -->
            <el-tab-pane v-if="canManageUsers" label="用户管理" name="users">
                <el-tabs v-model="userSubTab">
                    <el-tab-pane label="用户列表" name="list">
                        <div class="action-bar">
                            <h3>用户列表</h3>
                            <el-button type="primary" @click="openCreateUserDialog" icon="Plus">
                                添加用户
                            </el-button>
                        </div>
                        <el-card shadow="never">
                            <el-table :data="usersList" style="width: 100%" v-loading="usersLoading">
                                <el-table-column prop="username" label="用户名"></el-table-column>
                                <el-table-column prop="real_name" label="姓名"></el-table-column>
                                <el-table-column prop="role" label="角色">
                                    <template #default="scope">
                                        {{ getRoleName(scope.row.role) }}
                                    </template>
                                </el-table-column>
                                <el-table-column prop="college" label="学院"></el-table-column>
                                <el-table-column label="密码">
                                    <template #default="scope">
                                        ********
                                    </template>
                                </el-table-column>
                                <el-table-column prop="status" label="状态">
                                    <template #default="scope">
                                        <el-tag :type="scope.row.status === 'active' ? 'success' : (scope.row.status === 'rejected' ? 'danger' : 'warning')">
                                            {{ scope.row.status === 'active' ? '正常' : (scope.row.status === 'pending' ? '待审核' : (scope.row.status === 'rejected' ? '已驳回' : (scope.row.status || '未知'))) }}
                                        </el-tag>
                                    </template>
                                </el-table-column>
                                <el-table-column label="操作" width="240">
                                    <template #default="scope">
                                        <el-button size="small" @click="openEditUserDialog(scope.row)">编辑</el-button>
                                        <el-button size="small" type="primary" @click="openEditUserDialog(scope.row)">重置密码</el-button>
                                        <el-button size="small" type="danger" @click="deleteUser(scope.row)">删除</el-button>
                                    </template>
                                </el-table-column>
                            </el-table>
                        </el-card>
                    </el-tab-pane>
                    <el-tab-pane label="待审核用户" name="pending">
                        <div class="action-bar">
                            <h3>待审核用户</h3>
                            <el-button @click="fetchPendingUsers" icon="Refresh" circle></el-button>
                        </div>
                        <el-table :data="pendingUsers" style="width: 100%" v-loading="usersLoading">
                            <el-table-column prop="username" label="用户名"></el-table-column>
                            <el-table-column prop="real_name" label="姓名"></el-table-column>
                            <el-table-column prop="role" label="申请角色">
                                <template #default="scope">{{ getRoleName(scope.row.role) }}</template>
                            </el-table-column>
                            <el-table-column prop="college" label="学院"></el-table-column>
                            <el-table-column label="操作">
                                <template #default="scope">
                                    <el-button type="success" size="small" @click="approveUser(scope.row.id, 'approve')">通过</el-button>
                                    <el-button type="danger" size="small" @click="approveUser(scope.row.id, 'reject')">驳回</el-button>
                                </template>
                            </el-table-column>
                        </el-table>
                    </el-tab-pane>
                </el-tabs>
            </el-tab-pane>

            <!-- 3. 消息通知 -->
            <el-tab-pane label="消息通知" name="notifications">
                 <div class="action-bar">
                    <h3>我的消息</h3>
                    <el-button @click="fetchNotifications" icon="Refresh" circle></el-button>
                </div>
                <el-card shadow="never">
                    <el-table :data="notifications" style="width: 100%" :row-class-name="tableRowClassName">
                        <el-table-column prop="title" label="标题" width="180"></el-table-column>
                        <el-table-column prop="content" label="内容"></el-table-column>
                        <el-table-column prop="created_at" label="时间" width="180"></el-table-column>
                        <el-table-column label="操作" width="100">
                            <template #default="scope">
                                <el-button v-if="!scope.row.is_read" size="small" @click="markAsRead(scope.row)">标为已读</el-button>
                                <span v-else style="color: #999">已读</span>
                            </template>
                        </el-table-column>
                    </el-table>
                </el-card>
            </el-tab-pane>

            <!-- 4. 系统管理 (系统管理员可见) -->
            <el-tab-pane v-if="user?.role === 'system_admin'" label="系统管理" name="system">
                <div class="action-bar">
                    <h3>系统监控与备份</h3>
                    <div>
                         <el-button type="warning" @click="simulateRestart">系统重启</el-button>
                         <el-button type="primary" @click="backupSystem" :loading="backupLoading">数据备份</el-button>
                    </div>
                </div>
                <el-row :gutter="20" class="mt-4">
                    <el-col :span="12">
                        <el-card header="项目统计">
                            <el-table :data="systemStats.project_stats" stripe>
                                <el-table-column prop="status" label="状态">
                                    <template #default="scope">{{ getStatusInfo(scope.row.status).text }}</template>
                                </el-table-column>
                                <el-table-column prop="count" label="数量"></el-table-column>
                            </el-table>
                        </el-card>
                    </el-col>
                    <el-col :span="12">
                        <el-card header="用户统计">
                             <el-table :data="systemStats.user_stats" stripe>
                                <el-table-column prop="role" label="角色">
                                    <template #default="scope">{{ getRoleName(scope.row.role) }}</template>
                                </el-table-column>
                                <el-table-column prop="count" label="数量"></el-table-column>
                            </el-table>
                        </el-card>
                    </el-col>
                </el-row>
            </el-tab-pane>
        </el-tabs>

        <!-- 申请新项目弹窗 -->
        <el-dialog v-model="showCreateDialog" title="申请新项目" width="900px" destroy-on-close top="5vh" @close="handleDialogClose">
            <el-steps :active="activeStep" finish-status="success" align-center style="margin-bottom: 20px">
                <el-step title="基本信息"></el-step>
                <el-step title="详细信息"></el-step>
                <el-step title="团队成员"></el-step>
            </el-steps>

            <el-form :model="createForm" label-width="110px" ref="createFormRef" size="default">
                <!-- Dynamic Form Rendering (Step 1) -->
                <div v-show="activeStep === 0">
                    <template v-if="createForm.form_config?.groups && createForm.form_config.groups.length > 0">
                        <div v-for="(group, gIndex) in createForm.form_config.groups" :key="gIndex">
                            <el-divider v-if="group.title" content-position="left">{{ group.title }}</el-divider>
                            <el-row :gutter="20">
                                <el-col v-for="(field, fIndex) in group.fields" :key="fIndex" :span="field.type === 'textarea' || field.type === 'richtext' ? 24 : 12">
                                    <el-form-item :label="field.label" :required="field.required">
                                        <!-- Text Input -->
                                        <el-input v-if="field.type === 'text'" v-model="getFieldValue(createForm, field.key)" :placeholder="field.placeholder" :disabled="field.disabled"></el-input>
                                        
                                        <!-- Textarea -->
                                        <el-input v-if="field.type === 'textarea'" v-model="getFieldValue(createForm, field.key)" type="textarea" :rows="3" :placeholder="field.placeholder" :disabled="field.disabled"></el-input>
                                        
                                        <!-- Select -->
                                        <el-select v-if="field.type === 'select'" v-model="getFieldValue(createForm, field.key)" style="width: 100%" :placeholder="field.placeholder" :disabled="field.disabled" :filterable="true">
                                            <!-- Handle dynamic options vs static options -->
                                            <template v-if="field.key === 'project_type'">
                                                <el-option v-for="t in allowedProjectTypes" :key="t.value" :label="t.label" :value="t.value"></el-option>
                                            </template>
                                            <template v-else-if="field.key === 'college'">
                                                <el-option v-for="c in colleges" :key="c" :label="c" :value="c"></el-option>
                                            </template>
                                            <template v-else-if="field.key === 'inspiration_source'">
                                                 <!-- Special handling for inspiration source remote search -->
                                                 <el-option v-for="item in inspirationOptions" :key="item.value" :label="item.label" :value="item.value">
                                                    <span style="float: left">{{ item.label }}</span>
                                                    <span style="float: right; color: #8492a6; font-size: 13px">{{ item.summary ? item.summary.substring(0, 20) + '...' : '' }}</span>
                                                 </el-option>
                                            </template>
                                            <template v-else>
                                                <el-option v-for="opt in field.options" :key="opt.value" :label="opt.label" :value="opt.value"></el-option>
                                            </template>
                                        </el-select>
                                        
                                        <!-- Date -->
                                        <el-date-picker v-if="field.type === 'date'" v-model="getFieldValue(createForm, field.key)" type="date" value-format="YYYY-MM-DD" style="width: 100%" :placeholder="field.placeholder"></el-date-picker>
                                        
                                        <!-- Number -->
                                        <el-input-number v-if="field.type === 'number'" v-model="getFieldValue(createForm, field.key)" style="width: 100%" :min="0"></el-input-number>
                                        
                                        <!-- Radio -->
                                        <el-radio-group v-if="field.type === 'radio'" v-model="getFieldValue(createForm, field.key)">
                                            <el-radio v-for="opt in field.options" :key="opt.value" :label="opt.value">{{ opt.label }}</el-radio>
                                        </el-radio-group>

                                    </el-form-item>
                                </el-col>
                            </el-row>
                        </div>
                    </template>
                    <template v-else>
                        <!-- Fallback for legacy templates -->
                        <div style="text-align: center; color: #999;">表单配置为空，请联系管理员</div>
                    </template>
                </div>
                
                <!-- 步骤 2 -->
                <div v-show="activeStep === 1">
                    <template v-if="createForm.template_type === 'startup'">
                         <el-alert 
                            v-if="isMissingPitchMaterialsInForm"
                            :title="pitchMaterialAlertTitle" 
                            type="warning" 
                            show-icon
                            :closable="false" 
                            class="mb-4">
                         </el-alert>
                         <el-alert title="请上传相关证明材料 (支持 .pdf, .jpg, .png)" type="info" :closable="false" class="mb-4"></el-alert>
                         <el-form-item label="商业计划书 (PDF)">
                             <input type="file" @change="(e) => handleFileUpload(e, 'extra_info.attachments.business_plan')" accept=".pdf">
                             <div v-if="createForm.extra_info.attachments.business_plan" style="margin-top: 5px;">
                                 <el-tag type="success" style="margin-right: 10px;">已上传</el-tag>
                                 <el-link :href="createForm.extra_info.attachments.business_plan" target="_blank" type="primary" style="margin-right: 10px;">查看</el-link>
                                 <el-button type="danger" link size="small" @click="createForm.extra_info.attachments.business_plan = ''">删除</el-button>
                             </div>
                             <div style="font-size: 12px; color: #999;">PDF格式，不超过10MB</div>
                         </el-form-item>
                         <el-form-item label="路演PPT" required>
                             <input type="file" @change="(e) => handleFileUpload(e, 'extra_info.attachments.pitch_ppt')" accept=".pdf">
                             <div v-if="createForm.extra_info.attachments.pitch_ppt" style="margin-top: 5px;">
                                 <el-tag type="success" style="margin-right: 10px;">已上传</el-tag>
                                 <el-link :href="createForm.extra_info.attachments.pitch_ppt" target="_blank" type="primary" style="margin-right: 10px;">查看</el-link>
                                 <el-button type="danger" link size="small" @click="createForm.extra_info.attachments.pitch_ppt = ''">删除</el-button>
                             </div>
                         </el-form-item>
                         <el-form-item label="路演视频" required>
                             <input type="file" @change="(e) => handleFileUpload(e, 'extra_info.attachments.pitch_video')" accept=".mp4">
                             <div v-if="createForm.extra_info.attachments.pitch_video" style="margin-top: 5px;">
                                 <el-tag type="success" style="margin-right: 10px;">已上传</el-tag>
                                 <el-link :href="createForm.extra_info.attachments.pitch_video" target="_blank" type="primary" style="margin-right: 10px;">查看</el-link>
                                 <el-button type="danger" link size="small" @click="createForm.extra_info.attachments.pitch_video = ''">删除</el-button>
                             </div>
                             <div style="font-size: 12px; color: #999;">MP4格式，不超过25MB</div>
                         </el-form-item>
                         <el-form-item label="组织机构代码证">
                             <input type="file" @change="(e) => handleFileUpload(e, 'extra_info.attachments.org_code_cert')">
                             <span v-if="createForm.extra_info.attachments.org_code_cert" style="color: green; margin-left: 10px;">已上传</span>
                         </el-form-item>
                         <el-form-item label="专利/著作权">
                             <input type="file" @change="(e) => handleFileUpload(e, 'extra_info.attachments.patents')">
                             <span v-if="createForm.extra_info.attachments.patents" style="color: green; margin-left: 10px;">已上传</span>
                         </el-form-item>
                         <el-form-item label="营业执照">
                             <input type="file" @change="(e) => handleFileUpload(e, 'extra_info.attachments.business_license')">
                             <span v-if="createForm.extra_info.attachments.business_license" style="color: green; margin-left: 10px;">已上传</span>
                         </el-form-item>
                    </template>
                    <template v-else>
                        <el-form-item label="来源"><el-input v-model="createForm.source"></el-input></el-form-item>
                        <el-form-item label="考核指标"><el-input v-model="createForm.assessment_indicators" type="textarea" placeholder="请输入考核指标"></el-input></el-form-item>
                        <template v-if="createForm.project_type === 'innovation'">
                    <el-form-item label="背景"><el-input v-model="createForm.background" type="textarea" :disabled="createForm.status === 'school_approved'"></el-input></el-form-item>
                    <el-form-item label="内容"><el-input v-model="createForm.content" type="textarea" :disabled="createForm.status === 'school_approved'"></el-input></el-form-item>
                    <el-form-item label="创新点"><el-input v-model="createForm.innovation_point" type="textarea" :disabled="createForm.status === 'school_approved'"></el-input></el-form-item>
                    <el-form-item label="预期成果"><el-input v-model="createForm.expected_result" type="textarea" :disabled="createForm.status === 'school_approved'"></el-input></el-form-item>
                    <el-form-item label="风险控制"><el-input v-model="createForm.risk_control" type="textarea" placeholder="风险分析与控制" :disabled="createForm.status === 'school_approved'"></el-input></el-form-item>
                    <el-form-item label="经费"><el-input v-model="createForm.budget" :disabled="createForm.status === 'school_approved'"></el-input></el-form-item>
                    
                    <template v-if="createForm.status === 'school_approved'">
                        <el-divider content-position="left">路演材料 (必填)</el-divider>
                        <el-alert title="请提交路演PPT和视频材料" type="warning" :closable="false" show-icon class="mb-4"></el-alert>
                        <el-form-item label="商业计划书" required>
                            <input type="file" @change="(e) => handleFileUpload(e, 'extra_info.attachments.business_plan')" accept=".pdf">
                            <div v-if="createForm.extra_info.attachments.business_plan" style="margin-top: 5px;">
                                <el-tag type="success" style="margin-right: 10px;">已上传</el-tag>
                                <el-link :href="createForm.extra_info.attachments.business_plan" target="_blank" type="primary" style="margin-right: 10px;">查看</el-link>
                                <el-button type="danger" link size="small" @click="createForm.extra_info.attachments.business_plan = ''">删除</el-button>
                            </div>
                        </el-form-item>
                        <el-form-item label="路演PPT" required>
                            <input type="file" @change="(e) => handleFileUpload(e, 'extra_info.attachments.pitch_ppt')" accept=".pdf">
                            <div v-if="createForm.extra_info.attachments.pitch_ppt" style="margin-top: 5px;">
                                <el-tag type="success" style="margin-right: 10px;">已上传</el-tag>
                                <el-link :href="createForm.extra_info.attachments.pitch_ppt" target="_blank" type="primary" style="margin-right: 10px;">查看</el-link>
                                <el-button type="danger" link size="small" @click="createForm.extra_info.attachments.pitch_ppt = ''">删除</el-button>
                            </div>
                        </el-form-item>
                        <el-form-item label="路演视频" required>
                            <input type="file" @change="(e) => handleFileUpload(e, 'extra_info.attachments.pitch_video')" accept=".mp4">
                            <div v-if="createForm.extra_info.attachments.pitch_video" style="margin-top: 5px;">
                                <el-tag type="success" style="margin-right: 10px;">已上传</el-tag>
                                <el-link :href="createForm.extra_info.attachments.pitch_video" target="_blank" type="primary" style="margin-right: 10px;">查看</el-link>
                                <el-button type="danger" link size="small" @click="createForm.extra_info.attachments.pitch_video = ''">删除</el-button>
                            </div>
                            <div style="font-size: 12px; color: #999;">MP4格式，不超过25MB</div>
                        </el-form-item>
                    </template>
                </template>
                        <template v-else>
                     <el-form-item label="团队介绍"><el-input v-model="createForm.team_intro" type="textarea" :disabled="createForm.status === 'school_approved'"></el-input></el-form-item>
                     <el-form-item label="市场前景"><el-input v-model="createForm.market_prospect" type="textarea" :disabled="createForm.status === 'school_approved'"></el-input></el-form-item>
                     <el-form-item label="运营模式"><el-input v-model="createForm.operation_mode" type="textarea" :disabled="createForm.status === 'school_approved'"></el-input></el-form-item>
                     <el-form-item label="财务预算"><el-input v-model="createForm.financial_budget" :disabled="createForm.status === 'school_approved'"></el-input></el-form-item>
                     <el-form-item label="风险控制"><el-input v-model="createForm.risk_budget" type="textarea" :disabled="createForm.status === 'school_approved'"></el-input></el-form-item>
                </template>
                    </template>
                </div>

                <!-- 步骤 3 -->
                <div v-show="activeStep === 2">
                    <template v-if="createForm.template_type === 'startup'">
                        <el-divider content-position="left">项目负责人</el-divider>
                        <el-table :data="[createForm.extra_info.leader_info]" border style="margin-bottom: 20px">
                            <el-table-column label="姓名" min-width="100">
                                <template #default="scope">
                                    <el-input v-model="scope.row.name" placeholder="姓名"></el-input>
                                </template>
                            </el-table-column>
                            <el-table-column label="学号" min-width="120">
                                <template #default="scope">
                                    <el-input v-model="scope.row.id" placeholder="学号"></el-input>
                                </template>
                            </el-table-column>
                            <el-table-column label="学院" min-width="150">
                                <template #default="scope">
                                    <el-select v-model="scope.row.college" placeholder="学院" filterable>
                                        <el-option v-for="c in colleges" :key="c" :label="c" :value="c"></el-option>
                                    </el-select>
                                </template>
                            </el-table-column>
                            <el-table-column label="学历层次" min-width="120">
                                <template #default="scope">
                                    <el-select v-model="scope.row.degree" placeholder="学历">
                                        <el-option v-for="d in degrees" :key="d" :label="d" :value="d"></el-option>
                                    </el-select>
                                </template>
                            </el-table-column>
                            <el-table-column label="入学年份" min-width="100">
                                <template #default="scope">
                                    <el-input v-model="scope.row.year" placeholder="2022"></el-input>
                                </template>
                            </el-table-column>
                            <el-table-column label="毕业年份" min-width="100">
                                <template #default="scope">
                                    <el-input v-model="scope.row.grad_year" placeholder="2026"></el-input>
                                </template>
                            </el-table-column>
                            <el-table-column label="专业名称" min-width="120">
                                <template #default="scope">
                                    <el-input v-model="scope.row.major" placeholder="专业"></el-input>
                                </template>
                            </el-table-column>
                            <el-table-column label="联系电话" min-width="120">
                                <template #default="scope">
                                    <el-input v-model="scope.row.phone" placeholder="电话"></el-input>
                                </template>
                            </el-table-column>
                            <el-table-column label="邮箱" min-width="150">
                                <template #default="scope">
                                    <el-input v-model="scope.row.email" placeholder="邮箱"></el-input>
                                </template>
                            </el-table-column>
                        </el-table>
                        
                        <div style="margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-weight: bold;">团队主要成员</span>
                            <el-button size="small" @click="addMember">添加成员</el-button>
                        </div>
                        <el-table :data="createForm.members" border style="margin-bottom: 20px">
                            <el-table-column label="姓名" min-width="100">
                                <template #default="scope">
                                    <el-input v-model="scope.row.name" placeholder="姓名"></el-input>
                                </template>
                            </el-table-column>
                            <el-table-column label="学号" min-width="120">
                                <template #default="scope">
                                    <el-input v-model="scope.row.student_id" placeholder="学号"></el-input>
                                </template>
                            </el-table-column>
                            <el-table-column label="学院" min-width="150">
                                <template #default="scope">
                                    <el-select v-model="scope.row.college" placeholder="学院" filterable>
                                        <el-option v-for="c in colleges" :key="c" :label="c" :value="c"></el-option>
                                    </el-select>
                                </template>
                            </el-table-column>
                            <el-table-column label="学历层次" min-width="120">
                                <template #default="scope">
                                    <el-select v-model="scope.row.degree" placeholder="学历">
                                        <el-option v-for="d in degrees" :key="d" :label="d" :value="d"></el-option>
                                    </el-select>
                                </template>
                            </el-table-column>
                            <el-table-column label="入学年份" min-width="100">
                                <template #default="scope">
                                    <el-input v-model="scope.row.year" placeholder="2022"></el-input>
                                </template>
                            </el-table-column>
                            <el-table-column label="毕业年份" min-width="100">
                                <template #default="scope">
                                    <el-input v-model="scope.row.grad_year" placeholder="2026"></el-input>
                                </template>
                            </el-table-column>
                            <el-table-column label="专业名称" min-width="120">
                                <template #default="scope">
                                    <el-input v-model="scope.row.major" placeholder="专业"></el-input>
                                </template>
                            </el-table-column>
                            <el-table-column label="联系电话" min-width="120">
                                <template #default="scope">
                                    <el-input v-model="scope.row.phone" placeholder="电话"></el-input>
                                </template>
                            </el-table-column>
                            <el-table-column label="邮箱" min-width="150">
                                <template #default="scope">
                                    <el-input v-model="scope.row.email" placeholder="邮箱"></el-input>
                                </template>
                            </el-table-column>
                            <el-table-column label="操作" width="80" fixed="right">
                                <template #default="scope">
                                    <el-button link type="danger" @click="removeMember(scope.$index)">删除</el-button>
                                </template>
                            </el-table-column>
                        </el-table>
                    </template>
                    <template v-else>
                        <div style="margin-bottom: 10px; display: flex; justify-content: space-between;">
                            <span>成员列表</span>
                            <el-button size="small" @click="addMember">添加</el-button>
                        </div>
                        <el-table :data="createForm.members" border size="small">
                             <el-table-column label="姓名"><template #default="s"><el-input v-model="s.row.name" size="small"></el-input></template></el-table-column>
                             <el-table-column label="学号"><template #default="s"><el-input v-model="s.row.student_id" size="small"></el-input></template></el-table-column>
                             <el-table-column label="操作"><template #default="s"><el-button link type="danger" @click="removeMember(s.$index)">删</el-button></template></el-table-column>
                        </el-table>
                    </template>
                </div>
            </el-form>
            <template #footer>
                <el-button v-if="activeStep > 0" @click="activeStep--">上一步</el-button>
                <el-button v-if="activeStep < 2" type="primary" @click="nextStep">下一步</el-button>
                <el-button v-if="activeStep === 2" type="primary" @click="submitProject" :loading="submitting">提交</el-button>
            </template>
        </el-dialog>

        <!-- 添加用户弹窗 -->
        <el-dialog v-model="showCreateUserDialog" title="添加用户" width="500px">
            <el-form :model="createUserForm" label-width="80px">
                <el-form-item label="用户名" required><el-input v-model="createUserForm.username"></el-input></el-form-item>
                <el-form-item label="真实姓名" required><el-input v-model="createUserForm.real_name"></el-input></el-form-item>
                <el-form-item label="角色" required>
                    <el-select v-model="createUserForm.role" style="width: 100%">
                        <template v-if="user?.role === 'system_admin'">
                            <el-option label="项目管理员" value="project_admin"></el-option>
                            <el-option label="学院审批者" value="college_approver"></el-option>
                            <el-option label="学校审批者" value="school_approver"></el-option>
                            <el-option label="评委老师" value="judge"></el-option>
                        </template>
                        <template v-if="user?.role === 'project_admin'">
                            <el-option label="指导老师" value="teacher"></el-option>
                            <el-option label="学生" value="student"></el-option>
                        </template>
                    </el-select>
                </el-form-item>
                <el-form-item label="学院"><el-input v-model="createUserForm.college"></el-input></el-form-item>
                <el-form-item label="部门/专业"><el-input v-model="createUserForm.department"></el-input></el-form-item>
                <el-form-item label="证件号"><el-input v-model="createUserForm.identity_number" placeholder="学号/工号"></el-input></el-form-item>
                <el-form-item label="密码"><el-input v-model="createUserForm.password" placeholder="默认 123456" type="password" show-password></el-input></el-form-item>
            </el-form>
            <template #footer>
                <el-button @click="showCreateUserDialog = false">取消</el-button>
                <el-button type="primary" @click="submitCreateUser" :loading="submitting">确定</el-button>
            </template>
        </el-dialog>

        <!-- 编辑用户弹窗 -->
        <el-dialog v-model="showEditUserDialog" title="编辑用户" width="500px">
            <el-form :model="editUserForm" label-width="80px">
                <el-form-item label="用户名" required><el-input v-model="editUserForm.username" disabled></el-input></el-form-item>
                <el-form-item label="真实姓名" required><el-input v-model="editUserForm.real_name"></el-input></el-form-item>
                <el-form-item label="角色" required>
                    <el-select v-model="editUserForm.role" style="width: 100%">
                         <template v-if="user?.role === 'system_admin'">
                            <el-option label="项目管理员" value="project_admin"></el-option>
                            <el-option label="学院审批者" value="college_approver"></el-option>
                            <el-option label="学校审批者" value="school_approver"></el-option>
                            <el-option label="评委老师" value="judge"></el-option>
                            <el-option label="指导老师" value="teacher"></el-option>
                            <el-option label="学生" value="student"></el-option>
                        </template>
                        <template v-if="user?.role === 'project_admin'">
                            <el-option label="指导老师" value="teacher"></el-option>
                            <el-option label="学生" value="student"></el-option>
                        </template>
                    </el-select>
                </el-form-item>
                <el-form-item label="学院"><el-input v-model="editUserForm.college"></el-input></el-form-item>
                <el-form-item label="部门/专业"><el-input v-model="editUserForm.department"></el-input></el-form-item>
                <el-form-item label="证件号"><el-input v-model="editUserForm.identity_number" placeholder="学号/工号"></el-input></el-form-item>
                <el-form-item label="重置密码"><el-input v-model="editUserForm.password" placeholder="留空则不修改" type="password" show-password></el-input></el-form-item>
                <el-form-item label="临时密码">
                    <div style="display:flex;gap:8px;align-items:center;">
                        <el-input v-model="editUserForm.temp_password_display" placeholder="未生成" disabled style="flex:1;"></el-input>
                        <el-button size="small" type="primary" @click="generateTempPassword(editUserForm.id)">生成临时密码</el-button>
                    </div>
                </el-form-item>
            </el-form>
            <template #footer>
                <el-button @click="showEditUserDialog = false">取消</el-button>
                <el-button type="primary" @click="submitEditUser" :loading="submitting">保存</el-button>
            </template>
        </el-dialog>

        <!-- 审核/详情弹窗 -->
        <el-dialog v-model="showDetailDialog" :title="currentProject?.title" width="900px" top="5vh">
            <div v-if="currentProject">
                <el-tabs v-model="detailActiveTab">
                    <!-- Tab 1: 基本信息 -->
                    <el-tab-pane label="基本信息" name="basic">
                        <el-alert 
                            v-if="user?.role === 'student' && currentProject.status === 'school_approved' && currentProject.template_type === 'startup' && !currentProject.extra_info?.attachments?.business_plan"
                            title="提示：当前为待评审阶段，需补充上传商业计划书"
                            type="warning"
                            :closable="false"
                            class="mb-2">
                        </el-alert>
                        <el-button 
                            v-if="user?.role === 'student' && currentProject.status === 'school_approved' && currentProject.template_type === 'startup' && !currentProject.extra_info?.attachments?.business_plan"
                            type="primary" 
                            size="small" 
                            class="mb-4"
                            @click="openBusinessPlanUploadWithProject(currentProject)">
                            上传商业计划书
                        </el-button>
                        <el-form label-width="110px" disabled>
                            <template v-if="currentProject.template_type === 'startup'">
                                <el-divider content-position="left">基本信息</el-divider>
                                <el-row :gutter="20">
                                    <el-col :span="12"><el-form-item label="项目名称"><el-input :model-value="currentProject.title"></el-input></el-form-item></el-col>
                                    <el-col :span="12">
                                        <el-form-item label="项目分级">
                                            <el-select :model-value="currentProject.level" style="width: 100%">
                                                <el-option label="公益组" value="charity"></el-option>
                                                <el-option label="创业组" value="startup"></el-option>
                                                <el-option label="研究生组" value="grad"></el-option>
                                                <el-option label="本科生组" value="undergrad"></el-option>
                                            </el-select>
                                        </el-form-item>
                                    </el-col>
                                </el-row>
                                <el-row :gutter="20">
                                    <el-col :span="12">
                                        <el-form-item label="项目类别">
                                            <el-select :model-value="currentProject.project_type" style="width: 100%">
                                                <el-option label="创新训练" value="innovation"></el-option>
                                                <el-option label="创业训练" value="entrepreneurship_training"></el-option>
                                                <el-option label="创业实践" value="entrepreneurship_practice"></el-option>
                                            </el-select>
                                        </el-form-item>
                                    </el-col>
                                    <el-col :span="12"><el-form-item label="所在院系"><el-input :model-value="currentProject.college"></el-input></el-form-item></el-col>
                                </el-row>
                                <el-row :gutter="20">
                                    <el-col :span="12"><el-form-item label="成立时间"><el-input :model-value="currentProject.extra_info?.est_date"></el-input></el-form-item></el-col>
                                    <el-col :span="12">
                                        <el-form-item label="项目进展">
                                            <el-input :model-value="
                                                currentProject.extra_info?.progress === 'idea' ? '创意计划阶段' :
                                                currentProject.extra_info?.progress === 'registered_lt_3' ? '已注册公司运营（未满3年）' :
                                                currentProject.extra_info?.progress === 'registered_gt_3' ? '已注册公司运营（满3年）' :
                                                currentProject.extra_info?.progress === 'registered_funded' ? '已注册公司运营（获投资）' : currentProject.extra_info?.progress
                                            "></el-input>
                                        </el-form-item>
                                    </el-col>
                                </el-row>
                                <el-row :gutter="20">
                                    <el-col :span="12">
                                        <el-form-item label="学校科技成果转化">
                                            <el-radio-group :model-value="currentProject.extra_info?.tech_transfer">
                                                <el-radio label="yes">是</el-radio>
                                                <el-radio label="no">否</el-radio>
                                            </el-radio-group>
                                        </el-form-item>
                                    </el-col>
                                    <el-col :span="12">
                                        <el-form-item label="第一完成人">
                                            <el-radio-group :model-value="currentProject.extra_info?.first_creator">
                                                <el-radio label="yes">是</el-radio>
                                                <el-radio label="no">否</el-radio>
                                            </el-radio-group>
                                        </el-form-item>
                                    </el-col>
                                </el-row>

                                <el-divider content-position="left">企业信息</el-divider>
                                <el-row :gutter="20">
                                    <el-col :span="12"><el-form-item label="公司名称"><el-input :model-value="currentProject.extra_info?.company_info?.name"></el-input></el-form-item></el-col>
                                    <el-col :span="12"><el-form-item label="信用代码"><el-input :model-value="currentProject.extra_info?.company_info?.code"></el-input></el-form-item></el-col>
                                </el-row>
                                <el-row :gutter="20">
                                    <el-col :span="12"><el-form-item label="注册地"><el-input :model-value="currentProject.extra_info?.company_info?.location"></el-input></el-form-item></el-col>
                                    <el-col :span="12"><el-form-item label="注册资金"><el-input :model-value="currentProject.extra_info?.company_info?.capital"></el-input></el-form-item></el-col>
                                </el-row>
                                <el-form-item label="法人信息">
                                    <el-row :gutter="10">
                                        <el-col :span="8"><el-input :model-value="currentProject.extra_info?.company_info?.legal_rep?.name" placeholder="姓名"></el-input></el-col>
                                        <el-col :span="8"><el-input :model-value="currentProject.extra_info?.company_info?.legal_rep?.job" placeholder="职务"></el-input></el-col>
                                        <el-col :span="8"><el-input :model-value="currentProject.extra_info?.company_info?.legal_rep?.id" placeholder="身份证号"></el-input></el-col>
                                    </el-row>
                                </el-form-item>
                                
                                <el-divider content-position="left">股东信息</el-divider>
                                <el-table :data="currentProject.extra_info?.company_info?.shareholders" border size="small" style="margin-bottom: 20px;">
                                     <el-table-column label="股东名称" prop="name"></el-table-column>
                                     <el-table-column label="出资额(万元)" prop="amount"></el-table-column>
                                     <el-table-column label="比例(%)" prop="ratio"></el-table-column>
                                </el-table>

                                <el-divider content-position="left">获得投资情况</el-divider>
                                <el-table :data="currentProject.extra_info?.company_info?.investments" border size="small">
                                     <el-table-column label="投资方" prop="investor"></el-table-column>
                                     <el-table-column label="金额(万元)" prop="amount"></el-table-column>
                                     <el-table-column label="轮次" prop="stage"></el-table-column>
                                     <el-table-column label="时间" prop="date"></el-table-column>
                                </el-table>
                                
                                <el-divider content-position="left">指导老师</el-divider>
                                <el-row :gutter="20">
                                    <el-col :span="8"><el-form-item label="姓名"><el-input :model-value="currentProject.advisor_name"></el-input></el-form-item></el-col>
                                    <el-col :span="8"><el-form-item label="部门"><el-input :model-value="currentProject.extra_info?.advisor_info?.dept"></el-input></el-form-item></el-col>
                                    <el-col :span="8"><el-form-item label="职称"><el-input :model-value="currentProject.extra_info?.advisor_info?.title"></el-input></el-form-item></el-col>
                                </el-row>
                                <el-row :gutter="20">
                                    <el-col :span="12"><el-form-item label="电话"><el-input :model-value="currentProject.extra_info?.advisor_info?.phone"></el-input></el-form-item></el-col>
                                    <el-col :span="12"><el-form-item label="邮箱"><el-input :model-value="currentProject.extra_info?.advisor_info?.email"></el-input></el-form-item></el-col>
                                </el-row>
                                
                                <el-divider content-position="left">项目概述</el-divider>
                                <el-form-item label="概述"><el-input :model-value="currentProject.abstract" type="textarea" :rows="3"></el-input></el-form-item>
                                <el-form-item label="商业计划书">
                                     <el-link v-if="currentProject.extra_info?.attachments?.business_plan" :href="currentProject.extra_info.attachments.business_plan" target="_blank" type="primary">查看/下载</el-link>
                                     <span v-else>未上传 
                                        <el-button 
                                            v-if="user?.role === 'student' && currentProject.status === 'school_approved' && currentProject.template_type === 'startup'"
                                            type="primary" 
                                            link 
                                            size="small"
                                            @click="openBusinessPlanUploadWithProject(currentProject)">
                                            上传商业计划书
                                        </el-button>
                                     </span>
                                </el-form-item>
                            </template>
                            
                            <template v-else>
                                <el-form-item label="项目名称"><el-input :model-value="currentProject.title"></el-input></el-form-item>
                                <el-form-item label="项目类型">
                                    <el-select :model-value="currentProject.project_type" style="width: 100%">
                                        <el-option label="创新训练项目" value="innovation"></el-option>
                                        <el-option label="创业训练项目" value="entrepreneurship_training"></el-option>
                                        <el-option label="创业实践项目" value="entrepreneurship_practice"></el-option>
                                    </el-select>
                                </el-form-item>
                                <el-form-item label="项目摘要"><el-input :model-value="currentProject.abstract" type="textarea" :rows="3"></el-input></el-form-item>
                                <el-row :gutter="20">
                                    <el-col :span="12"><el-form-item label="级别"><el-select :model-value="currentProject.level"><el-option label="校级" value="school"></el-option></el-select></el-form-item></el-col>
                                    <el-col :span="12"><el-form-item label="年份"><el-input :model-value="currentProject.year"></el-input></el-form-item></el-col>
                                </el-row>
                                <el-row :gutter="20">
                                    <el-col :span="12"><el-form-item label="负责人"><el-input :model-value="currentProject.leader_name"></el-input></el-form-item></el-col>
                                    <el-col :span="12"><el-form-item label="指导老师"><el-input :model-value="currentProject.advisor_name"></el-input></el-form-item></el-col>
                                </el-row>
                            </template>
                        </el-form>
                    </el-tab-pane>

                    <!-- Tab 2: 项目详情 -->
                    <el-tab-pane label="项目详情" name="details">
                        <el-alert 
                            v-if="user?.role === 'student' && currentProject.status === 'school_approved' && currentProject.template_type === 'startup'"
                            title="提示：请点击下方“上传路演材料”进入详细信息上传相关材料"
                            type="warning"
                            :closable="false"
                            class="mb-2">
                        </el-alert>
                        <el-button 
                            v-if="user?.role === 'student' && currentProject.status === 'school_approved' && currentProject.template_type === 'startup'"
                            type="primary" 
                            size="small" 
                            class="mb-4"
                            @click="openPitchUploadWithProject(currentProject)">
                            上传路演材料
                        </el-button>
                        <el-form label-width="110px" disabled>
                            <template v-if="currentProject.template_type === 'startup'">
                                 <el-form-item label="组织机构代码证">
                                     <el-link v-if="currentProject.extra_info?.attachments?.org_code_cert" :href="currentProject.extra_info.attachments.org_code_cert" target="_blank" type="primary">查看/下载</el-link>
                                     <span v-else>未上传</span>
                                 </el-form-item>
                                 <el-form-item label="专利/著作权">
                                     <el-link v-if="currentProject.extra_info?.attachments?.patents" :href="currentProject.extra_info.attachments.patents" target="_blank" type="primary">查看/下载</el-link>
                                     <span v-else>未上传</span>
                                 </el-form-item>
                                 <el-form-item label="营业执照">
                                     <el-link v-if="currentProject.extra_info?.attachments?.business_license" :href="currentProject.extra_info.attachments.business_license" target="_blank" type="primary">查看/下载</el-link>
                                     <span v-else>未上传</span>
                                 </el-form-item>
                                 <el-form-item label="商业计划书" required>
                                     <el-link v-if="currentProject.extra_info?.attachments?.business_plan" :href="currentProject.extra_info.attachments.business_plan" target="_blank" type="primary">查看/下载</el-link>
                                     <span v-else>未上传</span>
                                 </el-form-item>
                                 <el-form-item label="路演PPT" required>
                                     <el-link v-if="currentProject.extra_info?.attachments?.pitch_ppt" :href="currentProject.extra_info.attachments.pitch_ppt" target="_blank" type="primary">查看/下载</el-link>
                                     <span v-else>未上传</span>
                                 </el-form-item>
                                 <el-form-item label="路演视频" required>
                                     <el-link v-if="currentProject.extra_info?.attachments?.pitch_video" :href="currentProject.extra_info.attachments.pitch_video" target="_blank" type="primary">查看/下载</el-link>
                                     <span v-else>未上传</span>
                                 </el-form-item>
                            </template>
                            <template v-else>
                                <el-form-item label="来源"><el-input :model-value="currentProject.project_source"></el-input></el-form-item>
                                <el-form-item label="考核指标"><el-input :model-value="currentProject.assessment_indicators" type="textarea"></el-input></el-form-item>
                                <template v-if="currentProject.project_type === 'innovation'">
                                    <el-form-item label="背景"><el-input :model-value="currentProject.background" type="textarea"></el-input></el-form-item>
                                    <el-form-item label="内容"><el-input :model-value="currentProject.content" type="textarea"></el-input></el-form-item>
                                    <el-form-item label="创新点"><el-input :model-value="currentProject.innovation_point" type="textarea"></el-input></el-form-item>
                                    <el-form-item label="预期成果"><el-input :model-value="currentProject.expected_result" type="textarea"></el-input></el-form-item>
                                    <el-form-item label="风险控制"><el-input :model-value="currentProject.risk_control" type="textarea"></el-input></el-form-item>
                                    <el-form-item label="经费"><el-input :model-value="currentProject.budget"></el-input></el-form-item>
                                </template>
                                <template v-else>
                                     <el-form-item label="团队介绍"><el-input :model-value="currentProject.team_intro" type="textarea"></el-input></el-form-item>
                                     <el-form-item label="市场前景"><el-input :model-value="currentProject.market_prospect" type="textarea"></el-input></el-form-item>
                                     <el-form-item label="运营模式"><el-input :model-value="currentProject.operation_mode" type="textarea"></el-input></el-form-item>
                                     <el-form-item label="财务预算"><el-input :model-value="currentProject.financial_budget"></el-input></el-form-item>
                                     <el-form-item label="风险控制"><el-input :model-value="currentProject.risk_budget" type="textarea"></el-input></el-form-item>
                                </template>
                            </template>
                        </el-form>
                    </el-tab-pane>

                    <!-- Tab 3: 团队成员 -->
                    <el-tab-pane label="团队成员" name="team">
                        <el-form label-width="110px" disabled>
                             <template v-if="currentProject.template_type === 'startup'">
                                <el-divider content-position="left">项目负责人</el-divider>
                                <el-table :data="[currentProject.extra_info?.leader_info || {}]" border style="margin-bottom: 20px">
                                    <el-table-column label="姓名" min-width="100">
                                        <template #default="scope"><el-input :model-value="scope.row.name"></el-input></template>
                                    </el-table-column>
                                    <el-table-column label="学号" min-width="120">
                                        <template #default="scope"><el-input :model-value="scope.row.id"></el-input></template>
                                    </el-table-column>
                                    <el-table-column label="学院" min-width="150">
                                        <template #default="scope">
                                            <el-select :model-value="scope.row.college" placeholder="学院" disabled>
                                                <el-option v-for="c in colleges" :key="c" :label="c" :value="c"></el-option>
                                            </el-select>
                                        </template>
                                    </el-table-column>
                                    <el-table-column label="学历层次" min-width="120">
                                        <template #default="scope">
                                            <el-select :model-value="scope.row.degree" placeholder="学历" disabled>
                                                <el-option v-for="d in degrees" :key="d" :label="d" :value="d"></el-option>
                                            </el-select>
                                        </template>
                                    </el-table-column>
                                    <el-table-column label="入学年份" min-width="100">
                                        <template #default="scope"><el-input :model-value="scope.row.year"></el-input></template>
                                    </el-table-column>
                                    <el-table-column label="毕业年份" min-width="100">
                                        <template #default="scope"><el-input :model-value="scope.row.grad_year"></el-input></template>
                                    </el-table-column>
                                    <el-table-column label="专业名称" min-width="120">
                                        <template #default="scope"><el-input :model-value="scope.row.major"></el-input></template>
                                    </el-table-column>
                                    <el-table-column label="联系电话" min-width="120">
                                        <template #default="scope"><el-input :model-value="scope.row.phone"></el-input></template>
                                    </el-table-column>
                                    <el-table-column label="邮箱" min-width="150">
                                        <template #default="scope"><el-input :model-value="scope.row.email"></el-input></template>
                                    </el-table-column>
                                </el-table>
                                
                                <el-divider content-position="left">团队主要成员</el-divider>
                                <el-table :data="currentProject.members ? currentProject.members.filter(m => !m.is_leader) : []" border style="margin-bottom: 20px">
                                    <el-table-column label="姓名" min-width="100">
                                        <template #default="scope"><el-input :model-value="scope.row.name"></el-input></template>
                                    </el-table-column>
                                    <el-table-column label="学号" min-width="120">
                                        <template #default="scope"><el-input :model-value="scope.row.student_id"></el-input></template>
                                    </el-table-column>
                                    <el-table-column label="学院" min-width="150">
                                        <template #default="scope">
                                            <el-select :model-value="scope.row.college" placeholder="学院" disabled>
                                                <el-option v-for="c in colleges" :key="c" :label="c" :value="c"></el-option>
                                            </el-select>
                                        </template>
                                    </el-table-column>
                                    <el-table-column label="学历层次" min-width="120">
                                        <template #default="scope">
                                            <el-select :model-value="scope.row.degree" placeholder="学历" disabled>
                                                <el-option v-for="d in degrees" :key="d" :label="d" :value="d"></el-option>
                                            </el-select>
                                        </template>
                                    </el-table-column>
                                    <el-table-column label="入学年份" min-width="100">
                                        <template #default="scope"><el-input :model-value="scope.row.year"></el-input></template>
                                    </el-table-column>
                                    <el-table-column label="毕业年份" min-width="100">
                                        <template #default="scope"><el-input :model-value="scope.row.grad_year"></el-input></template>
                                    </el-table-column>
                                    <el-table-column label="专业名称" min-width="120">
                                        <template #default="scope"><el-input :model-value="scope.row.major"></el-input></template>
                                    </el-table-column>
                                    <el-table-column label="联系电话" min-width="120">
                                        <template #default="scope"><el-input :model-value="scope.row.phone"></el-input></template>
                                    </el-table-column>
                                    <el-table-column label="邮箱" min-width="150">
                                        <template #default="scope"><el-input :model-value="scope.row.email"></el-input></template>
                                    </el-table-column>
                                </el-table>
                             </template>
                             <template v-else>
                                <div style="margin-bottom: 10px;">
                                    <span>成员列表</span>
                                </div>
                                <el-table :data="currentProject.members ? currentProject.members.filter(m => !m.is_leader) : []" border size="small">
                                     <el-table-column label="姓名" prop="name"></el-table-column>
                                     <el-table-column label="学号" prop="student_id"></el-table-column>
                                </el-table>
                             </template>
                        </el-form>
                    </el-tab-pane>

                    <!-- Tab 3.5: 过程管理 -->
                    <el-tab-pane label="过程管理" name="process" v-if="currentProject && (user?.role === 'student' || ['project_admin', 'system_admin', 'school_approver', 'college_approver', 'teacher', 'judge'].includes(user?.role))">
                        <el-timeline>
                            <!-- Midterm Check -->
                            <el-timeline-item :type="['midterm_submitted', 'midterm_advisor_approved', 'midterm_college_approved', 'midterm_approved', 'conclusion_submitted', 'conclusion_advisor_approved', 'conclusion_college_approved', 'finished'].includes(currentProject.status) ? 'success' : 'primary'" placement="top">
                                <el-card>
                                    <h4>中期检查</h4>
                                    <p v-if="currentProject.extra_info?.process_materials?.midterm_submitted_at">提交时间: {{ currentProject.extra_info.process_materials.midterm_submitted_at }}</p>
                                    
                                    <!-- Display Uploaded Files for Reviewers/Teachers -->
                                    <div v-if="currentProject.extra_info?.process_materials?.midterm" class="mb-2">
                                        <p><strong>提交材料:</strong></p>
                                        <ul style="list-style: none; padding-left: 0;">
                                            <li v-for="(url, key) in currentProject.extra_info.process_materials.midterm" :key="key" style="margin-bottom: 5px;">
                                                <el-tag size="small" style="margin-right: 5px;">{{ key === 'report' ? '中期报告' : (key === 'achievement' ? '阶段成果' : key) }}</el-tag>
                                                <el-link :href="url" target="_blank" type="primary">查看/下载</el-link>
                                            </li>
                                        </ul>
                                    </div>

                                    <!-- Feedback Display -->
                                    <div v-if="currentProject.extra_info?.midterm_advisor_feedback || currentProject.extra_info?.midterm_college_feedback || currentProject.extra_info?.midterm_school_feedback" class="mb-2 p-2 bg-gray-50 rounded">
                                         <p><strong>审核反馈:</strong></p>
                                         <div v-if="currentProject.extra_info?.midterm_advisor_feedback">
                                             <el-tag size="small" type="warning">导师</el-tag> {{ currentProject.extra_info.midterm_advisor_feedback }}
                                         </div>
                                         <div v-if="currentProject.extra_info?.midterm_college_feedback" class="mt-1">
                                             <el-tag size="small" type="success">学院</el-tag> {{ currentProject.extra_info.midterm_college_feedback }}
                                         </div>
                                          <div v-if="currentProject.extra_info?.midterm_school_feedback" class="mt-1">
                                             <el-tag size="small" type="primary">学校</el-tag> {{ currentProject.extra_info.midterm_school_feedback }}
                                         </div>
                                    </div>

                                    <div v-if="user?.role === 'student' && ['rated', 'midterm_rejected', 'midterm_submitted'].includes(currentProject.status)">
                                        <el-form label-width="120px">
                                            <el-form-item label="中期报告">
                                                <input type="file" @change="(e) => handleProcessUpload(e, 'midterm', 'report')" />
                                            </el-form-item>
                                            <el-form-item label="阶段成果">
                                                 <input type="file" @change="(e) => handleProcessUpload(e, 'midterm', 'achievement')" />
                                            </el-form-item>
                                            <el-button type="primary" @click="submitProcess('midterm')" :loading="submittingProcess">提交中期材料</el-button>
                                        </el-form>
                                    </div>
                                    <div v-else-if="currentProject.status === 'pending' || currentProject.status === 'submitted' || currentProject.status === 'advisor_approved' || currentProject.status === 'college_approved' || currentProject.status === 'school_approved'">
                                        <el-tag type="info">项目立项评审通过后方可提交</el-tag>
                                    </div>
                                     <div v-else>
                                        <el-tag :type="currentProject.status.includes('midterm') || ['conclusion_submitted', 'conclusion_advisor_approved', 'conclusion_college_approved', 'finished'].includes(currentProject.status) ? 'success' : 'info'">{{ getStatusTextForRow(currentProject) }}</el-tag>
                                    </div>
                                </el-card>
                            </el-timeline-item>
                            
                            <!-- Conclusion Check -->
                            <el-timeline-item :type="['conclusion_submitted', 'conclusion_advisor_approved', 'conclusion_college_approved', 'finished'].includes(currentProject.status) ? 'success' : 'primary'" placement="top">
                                <el-card>
                                    <h4>结题验收</h4>
                                    <p v-if="currentProject.extra_info?.process_materials?.conclusion_submitted_at">提交时间: {{ currentProject.extra_info.process_materials.conclusion_submitted_at }}</p>

                                    <!-- Display Uploaded Files for Reviewers/Teachers -->
                                    <div v-if="currentProject.extra_info?.process_materials?.conclusion" class="mb-2">
                                        <p><strong>提交材料:</strong></p>
                                        <ul style="list-style: none; padding-left: 0;">
                                            <li v-for="(url, key) in currentProject.extra_info.process_materials.conclusion" :key="key" style="margin-bottom: 5px;">
                                                <el-tag size="small" style="margin-right: 5px;">{{ key === 'report' ? '结题报告' : (key === 'achievement' ? '最终成果' : (key === 'supplement1' ? '补充材料1' : (key === 'supplement2' ? '补充材料2' : key))) }}</el-tag>
                                                <el-link :href="url" target="_blank" type="primary">查看/下载</el-link>
                                            </li>
                                        </ul>
                                    </div>

                                    <!-- Feedback Display -->
                                    <div v-if="currentProject.extra_info?.conclusion_advisor_feedback || currentProject.extra_info?.conclusion_college_feedback || currentProject.extra_info?.conclusion_school_feedback" class="mb-2 p-2 bg-gray-50 rounded">
                                         <p><strong>审核反馈:</strong></p>
                                         <div v-if="currentProject.extra_info?.conclusion_advisor_feedback">
                                             <el-tag size="small" type="warning">导师</el-tag> {{ currentProject.extra_info.conclusion_advisor_feedback }}
                                         </div>
                                         <div v-if="currentProject.extra_info?.conclusion_college_feedback" class="mt-1">
                                             <el-tag size="small" type="success">学院</el-tag> {{ currentProject.extra_info.conclusion_college_feedback }}
                                         </div>
                                          <div v-if="currentProject.extra_info?.conclusion_school_feedback" class="mt-1">
                                             <el-tag size="small" type="primary">学校</el-tag> {{ currentProject.extra_info.conclusion_school_feedback }}
                                         </div>
                                    </div>

                                    <div v-if="user?.role === 'student' && ['midterm_approved', 'conclusion_rejected', 'conclusion_submitted'].includes(currentProject.status)">
                                         <el-form label-width="120px">
                                            <el-form-item label="结题报告">
                                                <input type="file" @change="(e) => handleProcessUpload(e, 'conclusion', 'report')" />
                                            </el-form-item>
                                            <el-form-item label="最终成果">
                                                 <input type="file" @change="(e) => handleProcessUpload(e, 'conclusion', 'achievement')" />
                                            </el-form-item>
                                            <el-form-item label="补充材料1">
                                                 <input type="file" @change="(e) => handleProcessUpload(e, 'conclusion', 'supplement1')" />
                                            </el-form-item>
                                            <el-form-item label="补充材料2">
                                                 <input type="file" @change="(e) => handleProcessUpload(e, 'conclusion', 'supplement2')" />
                                            </el-form-item>
                                            <el-button type="primary" @click="submitProcess('conclusion')" :loading="submittingProcess">提交结题材料</el-button>
                                        </el-form>
                                    </div>
                                     <div v-else-if="!['conclusion_submitted', 'conclusion_advisor_approved', 'conclusion_college_approved', 'finished'].includes(currentProject.status)">
                                        <el-tag type="info">需通过中期检查后方可提交</el-tag>
                                    </div>
                                </el-card>
                            </el-timeline-item>
                        </el-timeline>
                    </el-tab-pane>

                    <!-- Tab 4: 审核与操作 -->
                    <el-tab-pane label="审批与材料" name="audit">
                         <div class="project-detail">
                            <el-descriptions :column="2" border>
                                <el-descriptions-item label="状态">{{ getStatusTextForRow(currentProject) }}</el-descriptions-item>
                                <el-descriptions-item label="当前ID">{{ currentProject.id }}</el-descriptions-item>
                            </el-descriptions>
                            
                            <div v-if="currentProject.status === 'rejected' || currentProject.status?.includes('_rejected')" class="mt-3">
                                <el-alert type="error" :closable="false">
                                    <template #title>
                                        驳回详情: {{
                                            currentProject.extra_info?.rejection_level ||
                                            (currentProject.school_feedback ? '学校' : (currentProject.college_feedback ? '学院' : (currentProject.extra_info?.advisor_feedback ? '导师' : '')))
                                        }} - 
                                        {{
                                            currentProject.extra_info?.rejection_reason ||
                                            currentProject.school_feedback ||
                                            currentProject.college_feedback ||
                                            currentProject.extra_info?.advisor_feedback || '未提供'
                                        }}
                                    </template>
                                </el-alert>
                            </div>

                            <!-- Reviews -->
                            <div v-if="currentProject.reviews && currentProject.reviews.length" class="mt-4">
                                <h4>评审记录</h4>
                                <el-table :data="currentProject.reviews" border size="small">
                                    <el-table-column prop="judge_name" label="评委"></el-table-column>
                                    <el-table-column prop="score" label="评分"></el-table-column>
                                    <el-table-column prop="comment" label="评语"></el-table-column>
                                </el-table>
                            </div>

                            <!-- Files -->
                            <div v-if="currentProject.files && currentProject.files.length" class="mt-4">
                                <h4>项目材料</h4>
                                <el-table :data="currentProject.files" border size="small">
                                    <el-table-column prop="file_type" label="类型">
                                        <template #default="scope">
                                            {{ scope.row.file_type === 'midterm' ? '中期报告' : '结项报告' }}
                                        </template>
                                    </el-table-column>
                                    <el-table-column prop="original_filename" label="文件名"></el-table-column>
                                    <el-table-column prop="created_at" label="提交时间"></el-table-column>
                                    <el-table-column label="操作">
                                         <template #default="scope">
                                             <el-button link type="primary" @click="downloadFile(scope.row)">下载</el-button>
                                         </template>
                                    </el-table-column>
                                </el-table>
                            </div>

                            <!-- Feedback History -->
                            <div v-if="currentProject.extra_info?.advisor_feedback || currentProject.college_feedback || currentProject.extra_info?.midterm_advisor_feedback" class="mt-4" style="background-color: #f0f9ff; padding: 15px; border-radius: 4px; border: 1px solid #bae6fd;">
                                <h4 style="margin-top: 0; color: #0284c7; margin-bottom: 10px;">审批意见记录</h4>
                                
                                <!-- Initial Phase -->
                                <div v-if="currentProject.extra_info?.advisor_feedback || currentProject.college_feedback" class="mb-2">
                                    <div v-if="currentProject.extra_info?.advisor_feedback" class="mb-1">
                                        <el-tag size="small" type="warning">导师(立项)</el-tag> {{ currentProject.extra_info.advisor_feedback }}
                                    </div>
                                    <div v-if="currentProject.college_feedback" class="mb-1">
                                        <el-tag size="small" type="success">学院(立项)</el-tag> {{ currentProject.college_feedback }}
                                    </div>
                                </div>

                                <!-- Midterm Phase -->
                                <div v-if="currentProject.status.includes('midterm') || currentProject.status.includes('conclusion') || currentProject.status === 'finished' || currentProject.status === 'rated'" class="mb-2">
                                     <div v-if="currentProject.extra_info?.midterm_advisor_feedback || currentProject.extra_info?.midterm_college_feedback">
                                         <div v-if="currentProject.extra_info?.midterm_advisor_feedback" class="mb-1">
                                             <el-tag size="small" type="warning">导师(中期)</el-tag> {{ currentProject.extra_info.midterm_advisor_feedback }}
                                         </div>
                                         <div v-if="currentProject.extra_info?.midterm_college_feedback" class="mb-1">
                                             <el-tag size="small" type="success">学院(中期)</el-tag> {{ currentProject.extra_info.midterm_college_feedback }}
                                         </div>
                                     </div>
                                </div>
                                
                                <!-- Conclusion Phase -->
                                <div v-if="currentProject.status.includes('conclusion') || currentProject.status === 'finished'" class="mb-2">
                                     <div v-if="currentProject.extra_info?.conclusion_advisor_feedback || currentProject.extra_info?.conclusion_college_feedback">
                                         <div v-if="currentProject.extra_info?.conclusion_advisor_feedback" class="mb-1">
                                             <el-tag size="small" type="warning">导师(结项)</el-tag> {{ currentProject.extra_info.conclusion_advisor_feedback }}
                                         </div>
                                         <div v-if="currentProject.extra_info?.conclusion_college_feedback" class="mb-1">
                                             <el-tag size="small" type="success">学院(结项)</el-tag> {{ currentProject.extra_info.conclusion_college_feedback }}
                                         </div>
                                     </div>
                                </div>
                            </div>

                            <!-- Audit Actions -->
                            <div v-if="canFileAudit(currentProject)" class="mt-4" style="background-color: #f9fafb; padding: 15px; border-radius: 4px; border: 1px solid #eaeaea;">
                                <h4>材料审核</h4>
                                <div class="el-input__wrapper" style="margin-bottom: 10px;">
                                    <input class="el-input__inner" v-model="fileAuditFeedback" placeholder="请输入审核意见（驳回时必填）" type="text" autocomplete="off">
                                </div>
                                
                                <div v-if="currentProject.status.includes('midterm')">
                                     <p style="margin-bottom: 10px;">当前阶段：<strong>中期检查</strong> ({{ getStatusInfo(currentProject.status).text }})。请审核上方提交的中期报告。</p>
                                     <el-button type="success" @click="auditFile('midterm', 'approve')">通过</el-button>
                                     <el-button type="danger" @click="auditFile('midterm', 'reject')">驳回</el-button>
                                </div>
                                <div v-else-if="currentProject.status.includes('conclusion')">
                                     <p style="margin-bottom: 10px;">当前阶段：<strong>结项审核</strong> ({{ getStatusInfo(currentProject.status).text }})。请审核上方提交的结项报告。</p>
                                     <el-button type="success" @click="auditFile('conclusion', 'approve')">通过</el-button>
                                     <el-button type="danger" @click="auditFile('conclusion', 'reject')">驳回</el-button>
                                </div>
                            </div>

                            <div v-if="isAuditing" class="audit-section mt-4 p-4 bg-gray-50">
                                <p>您即将<strong>{{ getStatusText(auditAction) || (auditAction === 'rejected' ? '驳回' : '通过') }}</strong>该项目</p>
                                <el-input v-model="auditFeedback" placeholder="审批意见" type="textarea"></el-input>
                            </div>
                         </div>
                    </el-tab-pane>
                </el-tabs>
            </div>
            <template #footer>
                <el-button @click="showDetailDialog = false">关闭</el-button>
                <el-button v-if="isAuditing" type="primary" @click="confirmAudit" :loading="submitting">提交审批</el-button>
            </template>
        </el-dialog>

        <!-- 评审弹窗 -->
        <el-dialog v-model="showReviewDialog" title="项目评审" width="500px">
            <el-form v-if="currentProject" label-width="80px">
                <el-form-item label="评分" required>
                    <el-input-number v-model="reviewForm.score" :min="0" :max="100"></el-input-number>
                </el-form-item>
                <el-form-item label="评语" required>
                    <el-input v-model="reviewForm.comment" type="textarea" :rows="3"></el-input>
                </el-form-item>
            </el-form>
            <template #footer>
                <el-button @click="showReviewDialog = false">取消</el-button>
                <el-button type="primary" @click="submitReview" :loading="submitting">提交评审</el-button>
            </template>
        </el-dialog>
        <el-dialog v-model="showUploadDialog" title="提交项目报告" width="500px">
            <el-form :model="uploadForm" label-width="80px">
                <el-form-item label="报告类型" required>
                    <el-tag>{{ uploadForm.file_type === 'midterm' ? '中期报告' : '结项报告' }}</el-tag>
                </el-form-item>
                <el-form-item label="文件名" required>
                    <el-input v-model="uploadForm.file_name" placeholder="请输入文件名"></el-input>
                </el-form-item>
            </el-form>
            <template #footer>
                <el-button @click="showUploadDialog = false">取消</el-button>
                <el-button type="primary" @click="submitUpload" :loading="submitting">提交</el-button>
            </template>
        </el-dialog>

        <!-- 发布公告弹窗 -->
        <el-dialog v-model="showAnnouncementDialog" title="发布公告/新闻" width="500px">
            <el-form :model="announcementForm" label-width="80px">
                <el-form-item label="类型" required>
                    <el-radio-group v-model="announcementForm.type">
                        <el-radio label="news">新闻</el-radio>
                        <el-radio label="notice">通知</el-radio>
                    </el-radio-group>
                </el-form-item>
                <el-form-item label="标题" required>
                    <el-input v-model="announcementForm.title" placeholder="请输入标题"></el-input>
                </el-form-item>
                <el-form-item label="内容" required>
                    <el-input v-model="announcementForm.content" type="textarea" :rows="4" placeholder="请输入内容"></el-input>
                </el-form-item>
            </el-form>
            <template #footer>
                <el-button @click="showAnnouncementDialog = false">取消</el-button>
                <el-button type="primary" @click="createAnnouncement">发布</el-button>
            </template>
        </el-dialog>
        <!-- 赛事发布/编辑弹窗 -->
        <el-dialog v-model="showCompDialog" :title="isEditingComp ? '编辑申报批次' : '发布申报批次'" width="600px">
            <el-form :model="compForm" label-width="100px">
                <el-form-item v-if="!isEditingComp" label="快速模板">
                    <div class="template-selection-container" style="width: 100%; border: 1px solid #dcdfe6; padding: 15px; border-radius: 4px;">
                        <!-- 大创体系 -->
                        <div class="template-group">
                            <div class="group-label" style="font-weight: bold; margin-bottom: 8px; color: #409EFF; border-left: 3px solid #409EFF; padding-left: 8px;">大创体系</div>
                            <el-radio-group v-model="selectedPreset" @change="applyPreset" style="display: flex; flex-direction: column; align-items: flex-start;">
                                <el-radio border label="innovation_program" style="margin-bottom: 8px; margin-left: 0; width: 100%;">大学生创新创业训练计划 (常规)</el-radio>
                                <el-radio border label="startup_practice" style="margin-left: 0; width: 100%;">创业实践专项项目</el-radio>
                            </el-radio-group>
                        </div>
                        
                        <!-- 竞赛体系 -->
                        <div class="template-group" style="margin-top: 15px;">
                            <div class="group-label" style="font-weight: bold; margin-bottom: 8px; color: #E6A23C; border-left: 3px solid #E6A23C; padding-left: 8px;">竞赛体系</div>
                            <el-radio-group v-model="selectedPreset" @change="applyPreset" style="display: flex; flex-direction: column; align-items: flex-start;">
                                <el-radio border label="internet_plus" style="margin-bottom: 8px; margin-left: 0; width: 100%;">“互联网+”大学生创新创业大赛</el-radio>
                                <el-radio border label="challenge_cup" style="margin-left: 0; width: 100%;">“挑战杯”大学生课外学术科技作品竞赛</el-radio>
                            </el-radio-group>
                        </div>
                    </div>
                    <div style="font-size: 12px; color: #999; margin-top: 5px;">选择模板可自动填充以下配置，您仍可手动修改。</div>
                </el-form-item>
                <el-divider v-if="!isEditingComp"></el-divider>

                <el-form-item label="批次名称" required>
                    <el-input v-model="compForm.title" placeholder="例如：2025年大学生创新创业训练计划"></el-input>
                </el-form-item>
                
                <el-form-item label="表单配置">
                    <el-button type="primary" @click="openFormDesigner">⚙️ 打开动态表单设计器</el-button>
                    <div style="margin-top: 5px; font-size: 12px; color: #666;">
                        当前包含 {{ compForm.form_config?.groups?.length || 0 }} 个分组，
                        {{ (compForm.form_config?.groups || []).reduce((acc, g) => acc + g.fields.length, 0) }} 个字段
                    </div>
                </el-form-item>

                <el-form-item label="批次级别">
                     <el-select v-model="compForm.level">
                         <el-option label="校级" value="School"></el-option>
                         <el-option label="省级" value="Provincial"></el-option>
                         <el-option label="国家级" value="National"></el-option>
                     </el-select>
                </el-form-item>
                <el-form-item label="申请模板">
                     <el-select v-model="compForm.template_type">
                         <el-option label="训练类模板 (Training)" value="training"></el-option>
                         <el-option label="竞赛类模板 (Competition)" value="competition"></el-option>
                     </el-select>
                </el-form-item>
                <el-form-item label="承办单位">
                    <el-input v-model="compForm.organizer"></el-input>
                </el-form-item>
                <el-form-item label="报名时间">
                     <el-col :span="11">
                         <el-date-picker v-model="compForm.registration_start" type="date" placeholder="开始日期" value-format="YYYY-MM-DD" style="width: 100%"></el-date-picker>
                     </el-col>
                     <el-col :span="2" class="text-center">-</el-col>
                     <el-col :span="11">
                         <el-date-picker v-model="compForm.registration_end" type="date" placeholder="结束日期" value-format="YYYY-MM-DD" style="width: 100%"></el-date-picker>
                     </el-col>
                </el-form-item>
                <el-form-item label="状态">
                    <el-select v-model="compForm.status">
                        <el-option label="进行中" value="active"></el-option>
                        <el-option label="未开始" value="upcoming"></el-option>
                        <el-option label="已结束" value="ended"></el-option>
                    </el-select>
                </el-form-item>
                <el-form-item label="描述/要求">
                    <el-input v-model="compForm.description" type="textarea" :rows="4"></el-input>
                </el-form-item>
                
                <el-divider content-position="left">基础属性配置</el-divider>
                <el-form-item label="批次性质">
                     <el-radio-group v-model="compForm.form_config.batch_type">
                         <el-radio label="program">常规训练项目</el-radio>
                         <el-radio label="competition">学科竞赛活动</el-radio>
                     </el-radio-group>
                </el-form-item>
                <el-form-item label="允许申报类型">
                     <el-checkbox-group v-model="compForm.form_config.allowed_project_types">
                         <el-checkbox label="innovation">创新训练</el-checkbox>
                         <el-checkbox label="entrepreneurship_training">创业训练</el-checkbox>
                         <el-checkbox label="entrepreneurship_practice">创业实践</el-checkbox>
                     </el-checkbox-group>
                </el-form-item>
            </el-form>
            <template #footer>
                <el-button @click="showCompDialog = false">取消</el-button>
                <el-button type="primary" @click="saveCompetition">保存</el-button>
            </template>
        </el-dialog>

        <!-- Form Designer Dialog -->
        <el-dialog v-model="showFormDesignerDialog" title="动态表单设计器" width="900px" top="5vh">
            <form-designer v-if="showFormDesignerDialog" v-model="currentFormConfig"></form-designer>
            <template #footer>
                <el-button @click="showFormDesignerDialog = false">取消</el-button>
                <el-button type="primary" @click="saveFormConfig">应用配置</el-button>
            </template>
        </el-dialog>

        <!-- 统计弹窗 -->
        <el-dialog v-model="showStatsDialog" title="系统统计" width="900px" @opened="initCharts">
            <el-row :gutter="20">
                <el-col :span="12">
                    <div id="statusChart" style="height: 300px;"></div>
                </el-col>
                <el-col :span="12">
                    <div id="collegeChart" style="height: 300px;"></div>
                </el-col>
            </el-row>
            <el-row :gutter="20" class="mt-4">
                 <el-col :span="12">
                    <div id="typeChart" style="height: 300px;"></div>
                </el-col>
                <el-col :span="12">
                    <el-card shadow="never">
                        <template #header>数据概览</template>
                        <p>总申报数: {{ systemStats.total_projects || (systemStats.project_stats ? systemStats.project_stats.reduce((a,b)=>a+b.count,0) : 0) }}</p>
                        <p>总用户数: {{ systemStats.total_users || (systemStats.user_stats ? systemStats.user_stats.reduce((a,b)=>a+b.count,0) : 0) }}</p>
                    </el-card>
                </el-col>
            </el-row>
        </el-dialog>

        <!-- 公告详情弹窗 -->
        <el-dialog v-model="showNoticeDialog" :title="currentNotice?.title" width="600px">
            <div v-if="currentNotice">
                <p style="white-space: pre-wrap; line-height: 1.6;">{{ currentNotice.content }}</p>
                <div style="text-align: right; color: #999; margin-top: 20px;">
                    发布人: {{ currentNotice.author_name || '管理员' }} <br>
                    时间: {{ currentNotice.created_at }}
                </div>
            </div>
        </el-dialog>
    </div>
    `,
    props: ['user'],
    data() {
        return {
            profileForm: {
                username: '',
                real_name: '',
                role: '',
                college: '',
                department: '',
                phone: '',
                email: '',
                personal_info: ''
            },
            passwordForm: {
                old_password: '',
                new_password: '',
                confirm_password: ''
            },
            savingProfile: false,
            activeTab: 'projects',
            userSubTab: 'list',
            projects: [],
            usersList: [],
            pendingUsers: [],
            loading: false,
            usersLoading: false,
            
            // Notifications
            notifications: [],
            lastCheckedNotificationId: 0,
            notificationTimer: null,
            
            // Announcements
            announcements: [],
            showAnnouncementDialog: false,
            announcementForm: { title: '', content: '', type: 'news' },

            // Competitions
            competitions: [],
            showCompDialog: false,
            showFormDesignerDialog: false,
            currentFormConfig: { groups: [] },
            selectedPreset: '',
            presetTemplates: [
                {
                    label: '大学生创新创业训练计划 (常规)',
                    value: 'innovation_program',
                    data: {
                        title: '202X年大学生创新创业训练计划',
                        level: 'School',
                        template_type: 'training',
                        organizer: '教务处',
                        form_config: {
                            batch_type: 'program',
                            allowed_project_types: ['innovation', 'entrepreneurship_training'],
                            groups: [
                                {
                                    title: '项目基本信息',
                                    fields: [
                                        { key: 'title', label: '项目名称', type: 'text', required: true, system: true },
                                        { key: 'project_type', label: '项目类型', type: 'select', required: true, system: true, options: [] },
                                        { key: 'extra_info.duration', label: '研究周期', type: 'select', required: true, options: [{label:'1年',value:'1'}, {label:'2年',value:'2'}] },
                                        { key: 'extra_info.subject', label: '所属学科', type: 'select', required: true, options: [] }, // Dynamic load in real app
                                        { key: 'abstract', label: '项目简介', type: 'richtext', required: true, system: true },
                                        { key: 'extra_info.innovation_points', label: '创新点描述', type: 'richtext', required: true },
                                        { key: 'extra_info.expected_outcomes', label: '预期成果', type: 'checkbox', required: true, options: [{label:'论文',value:'paper'}, {label:'专利',value:'patent'}, {label:'软著',value:'software'}, {label:'实物',value:'product'}, {label:'调研报告',value:'report'}] },
                                        { key: 'advisor_name', label: '指导教师', type: 'text', required: true, system: true }
                                    ]
                                },
                                {
                                    title: '团队与经费',
                                    fields: [
                                        { key: 'members', label: '团队成员', type: 'table', required: true, system: true },
                                        { key: 'extra_info.budget', label: '经费预算', type: 'table', required: true },
                                        { key: 'extra_info.attachments.application_doc', label: '申报书附件', type: 'file', required: true }
                                    ]
                                }
                            ]
                        }
                    }
                },
                {
                    label: '创业实践专项项目',
                    value: 'startup_practice',
                    data: {
                        title: '202X年创业实践项目申报',
                        level: 'School',
                        template_type: 'training',
                        organizer: '创新创业学院',
                        form_config: {
                            batch_type: 'program',
                            allowed_project_types: ['entrepreneurship_practice'],
                            groups: [
                                {
                                    title: '项目基本信息',
                                    fields: [
                                        { key: 'title', label: '项目名称', type: 'text', required: true, system: true },
                                        { key: 'project_type', label: '项目类别', type: 'select', required: true, system: true, options: [] },
                                        { key: 'level', label: '项目级别', type: 'select', required: true, system: true, options: [ {label:'校级',value:'school'}, {label:'省级',value:'provincial'}, {label:'国家级',value:'national'} ] },
                                        { key: 'college', label: '所在院系', type: 'select', required: true, system: true, options: [] },
                                        { key: 'year', label: '年份', type: 'text', required: true, system: true },
                                        { key: 'leader_name', label: '负责人', type: 'text', required: true, system: true, disabled: true },
                                        { key: 'advisor_name', label: '指导老师', type: 'text', required: true, system: true }
                                    ]
                                },
                                {
                                    title: '企业/实体信息',
                                    fields: [
                                        { key: 'extra_info.company_info.name', label: '公司名称', type: 'text', required: true },
                                        { key: 'extra_info.company_info.code', label: '统一社会信用代码', type: 'text', required: false },
                                        { key: 'extra_info.company_info.founded_date', label: '注册时间', type: 'date', required: false },
                                        { key: 'extra_info.company_info.capital', label: '注册资本(万元)', type: 'number', required: false },
                                        { key: 'extra_info.company_info.equity_structure', label: '股权结构', type: 'textarea', required: true, placeholder: '描述各成员持股比例' },
                                        { key: 'extra_info.park', label: '入驻园区', type: 'text', required: false },
                                        { key: 'extra_info.attachments.license', label: '营业执照', type: 'file', required: false }
                                    ]
                                },
                                {
                                    title: '项目进展',
                                    fields: [
                                        { key: 'extra_info.stage', label: '当前阶段', type: 'select', required: true, options: [{label:'创意',value:'idea'}, {label:'产品',value:'product'}, {label:'营收',value:'revenue'}, {label:'融资',value:'financing'}] },
                                        { key: 'extra_info.company_info.investments', label: '融资情况', type: 'table', required: false },
                                        { key: 'extra_info.total_funding', label: '累计融资金额(万元)', type: 'number', required: false }
                                    ]
                                },
                                {
                                    title: '商业模式',
                                    fields: [
                                        { key: 'extra_info.business_model', label: '商业模式', type: 'richtext', required: true },
                                        { key: 'extra_info.target_customers', label: '目标客户', type: 'textarea', required: true },
                                        { key: 'extra_info.competitive_advantage', label: '竞争优势', type: 'textarea', required: true }
                                    ]
                                },
                                {
                                    title: '附件材料',
                                    fields: [
                                        { key: 'extra_info.attachments.business_plan', label: '商业计划书', type: 'file', required: true },
                                        { key: 'extra_info.attachments.pitch_deck', label: '路演PPT', type: 'file', required: false },
                                        { key: 'extra_info.attachments.product_demo', label: '产品演示', type: 'file', required: false }
                                    ]
                                }
                            ]
                        }
                    }
                },
                {
                    label: '“互联网+”大学生创新创业大赛',
                    value: 'internet_plus',
                    data: {
                        title: '第九届“互联网+”大学生创新创业大赛校内选拔赛',
                        level: 'School',
                        template_type: 'competition',
                        organizer: '教务处',
                        form_config: {
                            batch_type: 'competition',
                            allowed_project_types: ['innovation', 'entrepreneurship_training', 'entrepreneurship_practice'],
                            groups: [
                                {
                                    title: '基本信息',
                                    fields: [
                                        { key: 'title', label: '项目名称', type: 'text', required: true, system: true },
                                        { key: 'extra_info.track', label: '参赛赛道', type: 'select', required: true, options: [{label:'高教主赛道',value:'main'}, {label:'红旅赛道',value:'red'}, {label:'产业命题赛道',value:'industry'}] },
                                        { key: 'extra_info.group', label: '参赛组别', type: 'select', required: true, options: [{label:'本科生创意组',value:'undergrad_idea'}, {label:'研究生创意组',value:'grad_idea'}, {label:'创业组',value:'startup'}, {label:'公益组',value:'charity'}] },
                                        { key: 'abstract', label: '项目简介', type: 'richtext', required: true, system: true },
                                        { key: 'extra_info.innovation_points', label: '创新点', type: 'textarea', required: true },
                                        { key: 'extra_info.pain_points', label: '行业痛点', type: 'textarea', required: true },
                                        { key: 'extra_info.business_model', label: '商业模式', type: 'richtext', required: true },
                                        { key: 'extra_info.competitor_analysis', label: '竞品分析', type: 'richtext', required: false },
                                        { key: 'advisor_name', label: '指导教师', type: 'text', required: true, system: true }
                                    ]
                                },
                                {
                                    title: '附件与成果',
                                    fields: [
                                        { key: 'members', label: '团队成员', type: 'table', required: true, system: true },
                                        { key: 'extra_info.attachments.business_plan', label: '商业计划书', type: 'file', required: true },
                                        { key: 'extra_info.attachments.pitch_deck', label: '路演PPT', type: 'file', required: true },
                                        { key: 'extra_info.attachments.video', label: '1分钟视频', type: 'file', required: false },
                                        { key: 'extra_info.awards', label: '获奖情况', type: 'table', required: false }
                                    ]
                                }
                            ]
                        }
                    }
                },
                {
                    label: '“挑战杯”大学生课外学术科技作品竞赛',
                    value: 'challenge_cup',
                    data: {
                        title: '第十八届“挑战杯”大学生课外学术科技作品竞赛',
                        level: 'School',
                        template_type: 'competition',
                        organizer: '校团委',
                        form_config: {
                            batch_type: 'competition',
                            allowed_project_types: ['innovation'],
                            groups: [
                                {
                                    title: '基本信息',
                                    fields: [
                                        { key: 'title', label: '作品名称', type: 'text', required: true, system: true },
                                        { key: 'extra_info.work_category', label: '作品类别', type: 'select', required: true, options: [{label:'自然科学类学术论文',value:'science_paper'}, {label:'哲学社会科学类社会调查报告',value:'social_report'}, {label:'科技发明制作',value:'tech_invention'}] },
                                        { key: 'extra_info.subject', label: '所属学科', type: 'select', required: true, options: [] },
                                        { key: 'abstract', label: '作品简介', type: 'richtext', required: true, system: true },
                                        { key: 'extra_info.research_background', label: '研究背景', type: 'richtext', required: true },
                                        { key: 'extra_info.research_method', label: '研究方法', type: 'textarea', required: true },
                                        { key: 'extra_info.innovation_points', label: '创新点', type: 'textarea', required: true },
                                        { key: 'extra_info.application_value', label: '应用价值', type: 'textarea', required: false },
                                        { key: 'advisor_name', label: '指导教师', type: 'text', required: true, system: true }
                                    ]
                                },
                                {
                                    title: '附件与成果',
                                    fields: [
                                        { key: 'members', label: '团队成员', type: 'table', required: true, system: true },
                                        { key: 'extra_info.attachments.full_paper', label: '论文/报告全文', type: 'file', required: true },
                                        { key: 'extra_info.attachments.plagiarism_report', label: '查重报告', type: 'file', required: true },
                                        { key: 'extra_info.attachments.supporting_materials', label: '支撑材料', type: 'file', required: false },
                                        { key: 'extra_info.awards', label: '获奖情况', type: 'table', required: false }
                                    ]
                                }
                            ]
                        }
                    }
                }
            ],
            compForm: { 
                title: '', level: 'School', organizer: '', registration_start: '', registration_end: '', status: 'active', 
                template_type: 'training',
                form_config: {
                    show_company_info: false,
                    show_advisor: true,
                    show_team_members: false,
                    show_attachments: true,
                    batch_type: 'program',
                    allowed_project_types: ['innovation', 'entrepreneurship_training', 'entrepreneurship_practice']
                }
            },
            isEditingComp: false,

            // System Stats
            systemStats: { project_stats: [], user_stats: [], college_stats: [], type_stats: [] },
            loadingStats: false,
            exporting: false,
            backupLoading: false,

            // File Upload
            showUploadDialog: false,
            uploadForm: { file_type: 'midterm', file_name: '' },
            
            // Create Project
            showCreateDialog: false,
            activeStep: 0,
            createForm: { title: '', project_type: 'innovation', members: [] },
            isEditing: false,
            currentEditingId: null,
            
            // Detail / Audit
            showDetailDialog: false,
            detailActiveTab: 'basic',
            currentProject: null,
            isAuditing: false,
            auditAction: '',
            auditFeedback: '',
            auditLevel: '', // New
            auditGrade: '', // New
            fileAuditFeedback: '',
            
            // Create User
            showCreateUserDialog: false,
            createUserForm: {},
            
            // Edit User
            showEditUserDialog: false,
            editUserForm: {},
            
            colleges: [
                "文学与新闻传播学院", "外语学院", "音乐舞蹈学院", "体育学院", "美术学院", 
                "法学院", "民族学与社会学学院", "马克思主义学院", "中华民族共同体学院", 
                "经济学院", "教育学院", "管理学院", "国家安全学院", "化学与材料科学学院", 
                "生命科学学院", "资源与环境学院", "药学院", "数学与统计学学院", 
                "电子信息工程学院（机器人学院）", "计算机学院（人工智能学院）", 
                "生物医学工程学院", "预科教育学院"
            ],
            degrees: ['大学专科', '大学本科', '硕士研究生', '博士研究生'],

            // Review
            showReviewDialog: false,
            reviewForm: { score: 80, comment: '' },
            
            submitting: false,
            submittingProcess: false,
            processFiles: { 
                midterm: { report: null, achievement: null }, 
                conclusion: { report: null, achievement: null } 
            },
            
            // New Dashboard Filters & Stats
            filters: {
                year: '',
                status: '',
                type: '',
                keyword: ''
            },
            showStatsDialog: false,
            statsData: {},
            showNoticeDialog: false,
            currentNotice: null,
            
            // Legacy Library
            legacyProjects: [],
            legacyKeyword: '',
            inspirationOptions: [],
            inspirationLoading: false
        }
    },
    computed: {
        canManageUsers() {
            return this.user?.role && ['system_admin', 'project_admin'].includes(this.user.role);
        },
        canManageSystem() {
            return this.user?.role && ['system_admin', 'project_admin'].includes(this.user.role);
        },
        filteredProjects() {
            console.log('DEBUG: filtering projects. Total raw:', this.projects.length);
            let base = Array.isArray(this.projects) 
                ? this.projects.filter(p => p && p.id !== undefined && p.id !== null && !isNaN(Number(p.id)) && Number(p.id) > 0)
                : [];
            console.log('DEBUG: after base filter:', base.length);
            
            // Keyword Filter (searchQuery or filters.keyword)
            const q = (this.filters.keyword || this.searchQuery || '').toLowerCase();
            if (q) {
                base = base.filter(p => 
                    p.title.toLowerCase().includes(q) || 
                    (p.leader_name && p.leader_name.toLowerCase().includes(q))
                );
            }
            
            // Year Filter
            if (this.filters.year) {
                base = base.filter(p => p.year === this.filters.year);
            }
            
            // Type Filter
            if (this.filters.type) {
                base = base.filter(p => p.project_type === this.filters.type);
            }
            
            // Status Filter
            if (this.filters.status) {
                if (this.filters.status === 'pending_audit') {
                    base = base.filter(p => this.canUserAudit(p));
                } else if (this.filters.status === 'approved') {
                    base = base.filter(p => ['rated', 'finished', 'midterm_approved'].includes(p.status));
                } else if (this.filters.status === 'rejected') {
                    base = base.filter(p => p.status.includes('rejected'));
                }
            }
            
            console.log('DEBUG: final filtered count:', base.length);
            return base;
        },
        missingPitchProjectsCount() {
            if (!this.user || this.user.role !== 'student') return 0;
            const getType = (p) => {
                if (!p.competition_id) return 'default';
                const comp = this.competitions.find(c => c.id === p.competition_id);
                return comp ? comp.template_type : 'default';
            };
            return this.projects.filter(p => {
                if (p.status !== 'school_approved') return false;
                if (getType(p) !== 'startup') return false;
                const a = p.extra_info?.attachments || {};
                return !a.pitch_ppt || !a.pitch_video;
            }).length;
        },
        isMissingPitchMaterialsInForm() {
            if (!this.createForm || this.createForm.template_type !== 'startup') return false;
            // 只有在评审阶段 (school_approved) 才强制检查
            if (this.createForm.status !== 'school_approved') return false;

            const attachments = this.createForm.extra_info?.attachments || {};
            const hasPPT = !!attachments.pitch_ppt;
            const hasVideo = !!attachments.pitch_video;
            
            return !hasPPT || !hasVideo;
        },
        pitchMaterialAlertTitle() {
            const attachments = this.createForm.extra_info?.attachments || {};
            const hasPPT = !!attachments.pitch_ppt;
            const hasVideo = !!attachments.pitch_video;
            
            if (!hasPPT && !hasVideo) return "评审阶段必填：请上传路演PPT和路演视频";
            if (!hasPPT) return "评审阶段必填：请上传路演PPT";
            if (!hasVideo) return "评审阶段必填：请上传路演视频";
            return "";
        },
        canViewReports() {
            return this.user?.role && ['system_admin', 'project_admin', 'school_approver', 'college_approver'].includes(this.user.role);
        },
        allowedProjectTypes() {
            const allTypes = [
                { label: '创新训练', value: 'innovation' },
                { label: '创业训练', value: 'entrepreneurship_training' },
                { label: '创业实践', value: 'entrepreneurship_practice' }
            ];
            
            if (!this.createForm.competition_id) return allTypes;
            
            const config = this.createForm.form_config;
            if (config && Array.isArray(config.allowed_project_types) && config.allowed_project_types.length > 0) {
                return allTypes.filter(t => config.allowed_project_types.includes(t.value));
            }
            
            return allTypes;
        }
    },
    async mounted() {
        this.fetchProjects();
        this.fetchAnnouncements(); // 获取公告
        this.fetchCompetitions(); // 获取赛事
        
        // Fetch notifications and show alert if unread
        await this.fetchNotifications();
        if (this.notifications && this.notifications.length > 0) {
            const unreadCount = this.notifications.filter(n => !n.is_read).length;
            if (unreadCount > 0) {
                ElementPlus.ElNotification({
                    title: '新消息提醒',
                    message: `您有 ${unreadCount} 条未读消息，请在消息中心查看。`,
                    type: 'info',
                    duration: 5000,
                    onClick: () => {
                        this.activeTab = 'notifications';
                    }
                });
            }
        }

        if (this.canManageUsers) {
            this.fetchUsers();
        }

        // If user is system_admin, fetch stats
        if (this.user?.role === 'system_admin') {
            this.fetchSystemStats();
        }
        
        // Start polling for new notifications every 10 seconds
        this.notificationTimer = setInterval(() => {
            this.checkNewNotifications();
        }, 10000);
    },
    beforeUnmount() {
        if (this.notificationTimer) {
            clearInterval(this.notificationTimer);
        }
    },
    watch: {
        'createForm.id': function(newVal, oldVal) {
             console.log(`DEBUG: createForm.id changed from ${oldVal} to ${newVal}`);
             if ([6, 7, 8, 9].includes(Number(newVal))) {
                 console.error(`CRITICAL: createForm.id set to Ghost ID (${newVal})! Stack trace:`, new Error().stack);
             }
        },
        'showCreateDialog': function(val) {
            if (!val) {
                console.log('DEBUG: showCreateDialog closed. Resetting createForm to prevent state leakage.');
                this.createForm = { id: undefined, title: '', project_type: 'innovation', members: [] };
                this.isEditing = false;
                this.currentEditingId = null;
                this.activeStep = 0;
            } else {
                console.log('DEBUG: showCreateDialog opened.');
            }
        },
        'createForm.extra_info.leader_info.college': {
            handler(val) {
                if (val && this.createForm.members) {
                    this.createForm.members.forEach(m => {
                        m.college = val;
                    });
                }
            },
            deep: true
        },
        'createForm.extra_info.leader_info.name': {
            handler(val) {
                if (!Array.isArray(this.createForm.members)) this.createForm.members = [];
                if (!this.createForm.members[0]) this.createForm.members[0] = {};
                this.createForm.members[0].name = val || '';
            }
        },
        'createForm.extra_info.leader_info.id': {
            handler(val) {
                if (!Array.isArray(this.createForm.members)) this.createForm.members = [];
                if (!this.createForm.members[0]) this.createForm.members[0] = {};
                this.createForm.members[0].student_id = val || '';
            }
        },
        'createForm.extra_info.leader_info.major': {
            handler(val) {
                if (!Array.isArray(this.createForm.members)) this.createForm.members = [];
                if (!this.createForm.members[0]) this.createForm.members[0] = {};
                this.createForm.members[0].major = val || '';
            }
        },
        'createForm.extra_info.leader_info.phone': {
            handler(val) {
                if (!Array.isArray(this.createForm.members)) this.createForm.members = [];
                if (!this.createForm.members[0]) this.createForm.members[0] = {};
                this.createForm.members[0].phone = val || '';
            }
        },
        'createForm.extra_info.leader_info.email': {
            handler(val) {
                if (!Array.isArray(this.createForm.members)) this.createForm.members = [];
                if (!this.createForm.members[0]) this.createForm.members[0] = {};
                this.createForm.members[0].email = val || '';
            }
        },
        'createForm.extra_info.leader_info.degree': {
            handler(val) {
                if (!Array.isArray(this.createForm.members)) this.createForm.members = [];
                if (!this.createForm.members[0]) this.createForm.members[0] = {};
                this.createForm.members[0].degree = val || '';
            }
        },
        'createForm.extra_info.leader_info.year': {
            handler(val) {
                if (!Array.isArray(this.createForm.members)) this.createForm.members = [];
                if (!this.createForm.members[0]) this.createForm.members[0] = {};
                this.createForm.members[0].year = val || '';
            }
        },
        'createForm.extra_info.leader_info.grad_year': {
            handler(val) {
                if (!Array.isArray(this.createForm.members)) this.createForm.members = [];
                if (!this.createForm.members[0]) this.createForm.members[0] = {};
                this.createForm.members[0].grad_year = val || '';
            }
        },
        activeTab(val) {
            if (val === 'users' && this.canManageUsers) {
                this.fetchUsers();
            } else if (val === 'projects') {
                this.fetchProjects();
            } else if (val === 'notifications') {
                this.fetchNotifications();
            } else if (val === 'system') {
                this.fetchSystemStats();
            } else if (val === 'reports' && this.canViewReports) {
                this.fetchStats();
            } else if (val === 'competitions' || val === 'comp_mgmt') {
                this.fetchCompetitions();
            } else if (val === 'pending' && this.canManageUsers) {
                this.fetchPendingUsers();
            } else if (val === 'profile') {
                this.initProfile();
            }
        },
        searchQuery(val) {
             // trigger re-render of computed
        }
    },
    methods: {
        // --- Profile Management ---
        initProfile() {
            if (this.user) {
                this.profileForm = { ...this.user };
                // 确保 passwordForm 被重置
                this.passwordForm = { old_password: '', new_password: '', confirm_password: '' };
            }
        },
        async updateProfile() {
            this.savingProfile = true;
            try {
                await axios.put('/api/me', this.profileForm);
                ElementPlus.ElMessage.success('个人信息更新成功');
                // 更新本地 user 对象
                this.$emit('login-success', { ...this.user, ...this.profileForm });
            } catch (e) {
                ElementPlus.ElMessage.error(e.response?.data?.error || '更新失败');
            } finally {
                this.savingProfile = false;
            }
        },
        async updatePassword() {
            if (this.passwordForm.new_password !== this.passwordForm.confirm_password) {
                ElementPlus.ElMessage.warning('两次输入的新密码不一致');
                return;
            }
            try {
                await axios.put('/api/me/password', this.passwordForm);
                ElementPlus.ElMessage.success('密码修改成功，请重新登录');
                this.$emit('logout');
                this.$router.push('/login');
            } catch (e) {
                ElementPlus.ElMessage.error(e.response?.data?.error || '修改失败');
            }
        },

        // --- Fetch Data ---
        async fetchCompetitions() {
            try {
                this.loading = true;
                const res = await axios.get(`/api/competitions?t=${new Date().getTime()}`);
                console.log('DEBUG: fetchCompetitions raw:', res.data);
                this.competitions = res.data;
                // this.syncCompetitionProjectMapping(); // Remove this function call as it might be causing issues if undefined
            } catch(e) { console.error(e); } finally { this.loading = false; }
        },
        async fetchLegacyProjects() {
            try {
                const res = await axios.get('/api/legacy', { params: { keyword: this.legacyKeyword } });
                this.legacyProjects = res.data;
            } catch (e) {
                console.error(e);
            }
        },
        async searchInspiration(query) {
            if (query !== '') {
                this.inspirationLoading = true;
                try {
                    const res = await axios.get('/api/legacy', { params: { keyword: query } });
                    this.inspirationOptions = res.data.map(item => ({
                        value: item.id,
                        label: item.title,
                        summary: item.methodology_summary
                    }));
                } catch(e) {
                    console.error(e);
                } finally {
                    this.inspirationLoading = false;
                }
            } else {
                this.inspirationOptions = [];
            }
        },
        async fetchNotifications() {
            try {
                const res = await axios.get('/api/notifications');
                // Filter out notifications related to Ghost IDs
                const filtered = Array.isArray(res.data) 
                    ? res.data.filter(n => !(n.related_id && [6, 7, 8, 9].includes(Number(n.related_id))) && !(n.content && (n.content.includes('ID: 6') || n.content.includes('ID: 7') || n.content.includes('ID: 8') || n.content.includes('ID: 9')))) 
                    : [];
                this.notifications = filtered;
                
                // Update lastCheckedNotificationId to the max ID present
                if (filtered.length > 0) {
                    const maxId = Math.max(...filtered.map(n => n.id));
                    if (this.lastCheckedNotificationId === 0) {
                        this.lastCheckedNotificationId = maxId;
                    }
                }
            } catch(e) { console.error(e); }
        },
        async checkNewNotifications() {
            try {
                const res = await axios.get('/api/notifications');
                const filtered = Array.isArray(res.data) 
                    ? res.data.filter(n => !(n.related_id && [6, 7, 8, 9].includes(Number(n.related_id))) && !(n.content && (n.content.includes('ID: 6') || n.content.includes('ID: 7') || n.content.includes('ID: 8') || n.content.includes('ID: 9')))) 
                    : [];
                
                // Find notifications with ID > lastCheckedNotificationId
                const newNotifications = filtered.filter(n => n.id > this.lastCheckedNotificationId);
                
                if (newNotifications.length > 0) {
                    newNotifications.forEach(n => {
                        ElementPlus.ElNotification({
                            title: n.title || '新消息提醒',
                            message: n.content,
                            type: n.type === 'error' ? 'error' : (n.type === 'warning' ? 'warning' : 'info'),
                            duration: 8000,
                            onClick: () => {
                                this.activeTab = 'notifications';
                            }
                        });
                    });
                    
                    // Update list and max ID
                    this.notifications = filtered;
                    this.lastCheckedNotificationId = Math.max(...filtered.map(n => n.id));
                }
                
                // Also refresh announcements silently
                this.fetchAnnouncements();
            } catch(e) { console.error(e); }
        },
        async fetchAnnouncements() {
            try {
                const res = await axios.get('/api/announcements');
                this.announcements = res.data;
            } catch(e) { console.error(e); }
        },
        async fetchStats() {
            this.loadingStats = true;
            try {
                const res = await axios.get('/api/system/stats');
                this.systemStats = res.data;
                this.$nextTick(() => {
                    this.renderCharts();
                });
            } catch(e) { console.error(e); }
            finally { this.loadingStats = false; }
        },
        renderCharts() {
            // Check if echarts is loaded
            if (typeof echarts === 'undefined') {
                console.error('ECharts is not loaded');
                return;
            }

            // Status Chart
            if (this.$refs.chartStatus) {
                const chart = echarts.init(this.$refs.chartStatus);
                chart.setOption({
                    tooltip: { trigger: 'item' },
                    legend: { top: '5%', left: 'center' },
                    series: [
                        {
                            name: '项目状态',
                            type: 'pie',
                            radius: ['40%', '70%'],
                            avoidLabelOverlap: false,
                            itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
                            label: { show: false, position: 'center' },
                            emphasis: { label: { show: true, fontSize: '20', fontWeight: 'bold' } },
                            labelLine: { show: false },
                            data: this.systemStats.project_stats.map(s => ({ value: s.count, name: this.getStatusInfo(s.status).text }))
                        }
                    ]
                });
            }
            
            // Type Chart
            if (this.$refs.chartType) {
                const chart = echarts.init(this.$refs.chartType);
                const getTypeLabel = (t) => {
                     const map = {
                         'innovation': '创新训练',
                         'entrepreneurship_training': '创业训练',
                         'entrepreneurship_practice': '创业实践'
                     };
                     return map[t] || t;
                };
                chart.setOption({
                    tooltip: { trigger: 'item' },
                    legend: { top: '5%', left: 'center' },
                    series: [
                        {
                            name: '项目类型',
                            type: 'pie',
                            radius: '50%',
                            data: this.systemStats.type_stats.map(s => ({ value: s.count, name: getTypeLabel(s.project_type) })),
                            emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' } }
                        }
                    ]
                });
            }
            
            // College Chart
            if (this.$refs.chartCollege) {
                const chart = echarts.init(this.$refs.chartCollege);
                chart.setOption({
                    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
                    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
                    xAxis: [ { type: 'category', data: this.systemStats.college_stats.map(s => s.college), axisTick: { alignWithLabel: true }, axisLabel: { rotate: 45, interval: 0 } } ],
                    yAxis: [ { type: 'value' } ],
                    series: [
                        {
                            name: '项目数量',
                            type: 'bar',
                            barWidth: '60%',
                            data: this.systemStats.college_stats.map(s => s.count)
                        }
                    ]
                });
            }
        },
        async downloadReport() {
            this.exporting = true;
            try {
                const response = await axios.get('/api/reports/export', { responseType: 'blob' });
                const url = window.URL.createObjectURL(new Blob([response.data]));
                const link = document.createElement('a');
                link.href = url;
                link.setAttribute('download', 'projects_report.csv');
                document.body.appendChild(link);
                link.click();
                link.remove();
                window.URL.revokeObjectURL(url);
                ElementPlus.ElMessage.success('报表导出成功');
            } catch (e) {
                console.error(e);
                ElementPlus.ElMessage.error('导出失败: ' + (e.response?.data?.error || e.message));
            } finally {
                this.exporting = false;
            }
        },
        async fetchSystemStats() {
            try {
                const res = await axios.get('/api/system/stats');
                this.systemStats = res.data;
            } catch(e) { console.error(e); }
        },
        async fetchProjects() {
            this.loading = true;
            try {
                console.log('DEBUG: fetchProjects calling API...');
                const res = await axios.get(`/api/projects?t=${new Date().getTime()}`);
                console.log('DEBUG: fetchProjects API response:', res.data);
                if (Array.isArray(res.data)) {
                    const ids = res.data.map(p => p.id);
                    console.log('DEBUG: fetchProjects IDs:', ids);
                    if (ids.includes(6) || ids.includes('6') || ids.includes(7) || ids.includes('7')) {
                        console.error('CRITICAL: API returned Ghost ID (6 or 7)! Project data:', res.data.find(p => p.id == 6 || p.id == 7));
                    }
                }
                // Filter out invalid projects (ghosts)
                this.projects = Array.isArray(res.data) 
                    ? res.data.filter(p => p && p.id && !isNaN(Number(p.id)) && Number(p.id) > 0 && ![6, 7, 8, 9].includes(Number(p.id))) 
                    : [];
                this.syncCompetitionProjectMapping();
                
                // Legacy Prompt Check
                if (this.user?.role === 'student') {
                    const candidate = this.projects.find(p => 
                        p.status === 'finished' && 
                        p.final_grade === '优秀' && 
                        (!p.extra_info || !p.extra_info.legacy_prompted) &&
                        p.created_by === this.user?.id
                    );
                    
                    if (candidate) {
                        ElementPlus.ElMessageBox.confirm(
                            `恭喜！您的项目《${candidate.title}》荣获“优秀”评级。是否同意将本项目的经验总结收录至往届经验库，供学弟学妹们参考？`,
                            '经验传承',
                            {
                                confirmButtonText: '同意收录',
                                cancelButtonText: '暂不收录',
                                type: 'success'
                            }
                        ).then(async () => {
                            try {
                                // Fetch Reviews for comments (optional, skip for now or use placeholder)
                                await axios.post('/api/legacy', {
                                    original_project_id: candidate.id,
                                    title: candidate.title,
                                    methodology_summary: candidate.abstract || '暂无总结',
                                    expert_comments: '评审组一致认可', // Placeholder
                                    ppt_url: candidate.extra_info?.attachments?.pitch_ppt || ''
                                });
                                ElementPlus.ElMessage.success('收录成功！感谢您的贡献。');
                            } catch(e) { console.error(e); }
                            
                            const extra = candidate.extra_info || {};
                            extra.legacy_prompted = true;
                            await axios.put(`/api/projects/${candidate.id}`, { extra_info: extra });
                        }).catch(async () => {
                            const extra = candidate.extra_info || {};
                            extra.legacy_prompted = true;
                            await axios.put(`/api/projects/${candidate.id}`, { extra_info: extra });
                        });
                    }
                }
            } catch (e) { console.error(e); } 
            finally { this.loading = false; }
        },
        async fetchUsers() {
            this.usersLoading = true;
            try {
                const res = await axios.get('/api/users');
                this.usersList = res.data;
            } catch (e) { 
                console.error(e); 
                ElementPlus.ElMessage.error(e.response?.data?.error || '获取用户失败'); 
            } 
            finally { this.usersLoading = false; }
        },
        async fetchPendingUsers() {
            this.usersLoading = true;
            try {
                const res = await axios.get('/api/users', { params: { status: 'pending' } });
                this.pendingUsers = res.data;
                if (!Array.isArray(this.pendingUsers)) this.pendingUsers = [];
            } catch (e) { 
                console.error(e); 
                ElementPlus.ElMessage.error(e.response?.data?.error || '获取待审核用户失败'); 
            } 
            finally { this.usersLoading = false; }
        },
        async approveUser(uid, action) {
            try {
                await axios.put(`/api/users/${uid}/approve`, { action });
                ElementPlus.ElMessage.success(action === 'approve' ? '已通过' : '已驳回');
                this.fetchPendingUsers();
                // 如果当前列表也显示所有用户，则一并刷新
                if (this.canManageUsers) this.fetchUsers();
            } catch (e) {
                ElementPlus.ElMessage.error(e.response?.data?.error || '操作失败');
            }
        },
        
        // --- Process Management ---
        handleProcessUpload(event, stage, type) {
            const file = event.target.files[0];
            if (!file) return;
            
            // Limit file size (e.g. 20MB)
            if (file.size > 20 * 1024 * 1024) {
                ElementPlus.ElMessage.error('文件大小不能超过20MB');
                event.target.value = '';
                return;
            }

            const formData = new FormData();
            formData.append('file', file);

            // Upload to generic upload endpoint
            axios.post('/api/common/upload', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            }).then(res => {
                if (!this.processFiles[stage]) this.processFiles[stage] = {};
                this.processFiles[stage][type] = res.data.url; // Store URL
                ElementPlus.ElMessage.success('文件上传成功');
            }).catch(e => {
                console.error(e);
                ElementPlus.ElMessage.error('上传失败: ' + (e.response?.data?.error || e.message));
                event.target.value = ''; // Reset input
            });
        },

        async submitProcess(stage) {
            if (!this.currentProject) {
                ElementPlus.ElMessage.error('当前项目数据异常，请重新打开详情页');
                return;
            }
            
            // 简单的客户端校验
            if (!this.processFiles[stage] || Object.keys(this.processFiles[stage]).length === 0) {
                ElementPlus.ElMessage.warning('请先上传文件');
                return;
            }

            this.submittingProcess = true;
            try {
                const endpoint = stage === 'midterm' ? 'midterm' : 'conclusion';
                const payload = {
                    attachments: this.processFiles[stage] || {}
                };
                
                // Ensure ID is valid
                if (!this.currentProject.id) {
                     console.error('CRITICAL: currentProject has no ID:', this.currentProject);
                     throw new Error('Project ID is missing in frontend state');
                }
                
                const url = `/api/projects/${this.currentProject.id}/${endpoint}`;
                console.log(`Submitting to ${url} with payload:`, payload);
                console.log('DEBUG: Submitting Project State:', JSON.parse(JSON.stringify(this.currentProject)));
                
                await axios.post(url, payload);
                ElementPlus.ElMessage.success('提交成功');
                // Refresh data
                await this.fetchProjects();
                // Update currentProject to reflect changes
                const updated = this.projects.find(p => p.id === this.currentProject.id);
                if (updated) this.currentProject = updated;
                else {
                    // Fallback re-fetch detail if list update failed to include it
                    const res = await axios.get(`/api/projects/${this.currentProject.id}`);
                    this.currentProject = res.data;
                }
                
            } catch (e) {
                console.error('Submit Process Error:', e);
                ElementPlus.ElMessage.error(e.response?.data?.error || e.message || '提交失败');
            } finally {
                this.submittingProcess = false;
            }
        },

        exportProjects() {
            this.downloadReport();
        },
        viewAnnouncement(notice) {
            this.currentNotice = notice;
            this.showNoticeDialog = true;
        },
        async initCharts() {
            try {
                await this.fetchSystemStats();
                // Ensure DOM is updated
                this.$nextTick(() => {
                    if (document.getElementById('statusChart')) {
                        const statusChart = echarts.init(document.getElementById('statusChart'));
                        statusChart.setOption({
                            title: { text: '项目状态分布', left: 'center' },
                            tooltip: { trigger: 'item' },
                            series: [{
                                type: 'pie',
                                radius: '50%',
                                data: this.systemStats.project_stats.map(s => ({ name: this.getStatusInfo(s.status).text, value: s.count }))
                            }]
                        });
                    }
                    
                    if (document.getElementById('collegeChart')) {
                        const collegeChart = echarts.init(document.getElementById('collegeChart'));
                        collegeChart.setOption({
                            title: { text: '学院申报分布', left: 'center' },
                            tooltip: { trigger: 'axis' },
                            xAxis: { type: 'category', data: this.systemStats.college_stats.map(s => s.college), axisLabel: { rotate: 45 } },
                            yAxis: { type: 'value' },
                            series: [{
                                type: 'bar',
                                data: this.systemStats.college_stats.map(s => s.count)
                            }]
                        });
                    }
                    
                    if (document.getElementById('typeChart')) {
                        const typeChart = echarts.init(document.getElementById('typeChart'));
                        typeChart.setOption({
                            title: { text: '项目类型分布', left: 'center' },
                            tooltip: { trigger: 'item' },
                            series: [{
                                type: 'pie',
                                radius: ['40%', '70%'],
                                data: this.systemStats.type_stats.map(s => ({ 
                                    name: s.project_type === 'innovation' ? '创新训练' : (s.project_type === 'entrepreneurship_training' ? '创业训练' : '创业实践'), 
                                    value: s.count 
                                }))
                            }]
                        });
                    }
                });
            } catch (e) {
                console.error(e);
            }
        },
        
        // --- Helpers ---
        getRoleName(role) {
            const map = {
                system_admin: '系统管理员', project_admin: '项目管理员',
                college_approver: '学院审批者', school_approver: '学校审批者',
                judge: '评委老师', teacher: '指导老师', student: '学生'
            };
            return map[role] || role;
        },
        getProjectType(type) {
            return type === 'innovation' ? '创新训练' : (type === 'entrepreneurship_training' ? '创业训练' : '创业实践');
        },
        getStatusInfo(status) {
            const map = {
                ...STATUS_MAP,
                'advisor_approved': { text: '导师已审', type: 'info' },
                'midterm_submitted': { text: '中期提交', type: 'primary' },
                'midterm_advisor_approved': { text: '中期导师通过', type: 'success' },
                'midterm_college_approved': { text: '中期学院通过', type: 'success' },
                'midterm_approved': { text: '中期通过', type: 'success' },
                'conclusion_submitted': { text: '结项提交', type: 'primary' },
                'conclusion_advisor_approved': { text: '结项导师通过', type: 'success' },
                'conclusion_college_approved': { text: '结项学院通过', type: 'success' },
                'finished': { text: '已结项', type: 'success' }
            };
            return map[status] || STATUS_MAP[status] || { text: status, type: 'info' };
        },
        getStatusText(status) { return this.getStatusInfo(status).text; },
        getStatusType(status) { return this.getStatusInfo(status).type; },
        getStatusTextForRow(row) {
            const base = this.getStatusInfo(row.status).text;
            const isRejected = row.status === 'rejected' || (typeof row.status === 'string' && row.status.endsWith('_rejected'));
            if (!isRejected) return base;
            const level = row.extra_info?.rejection_level
                || (row.school_feedback ? '学校' : (row.college_feedback ? '学院' : (row.extra_info?.advisor_feedback ? '学院（导师）' : '')));
            return level ? `${level}已驳回` : base;
        },
        
        // --- Permissions ---
        canUserAudit(project) {
            const role = this.user?.role;
            if (!role) return false;
            const status = project.status;
            
            if (role === 'teacher') {
                return ['pending', 'midterm_submitted', 'conclusion_submitted'].includes(status);
            }
            if (role === 'college_approver') {
                return ['advisor_approved', 'midterm_advisor_approved', 'conclusion_advisor_approved'].includes(status);
            }
            if (role === 'school_approver') {
                return ['college_approved', 'midterm_college_approved', 'conclusion_college_approved'].includes(status);
            }
            return false;
        },
        canFileAudit(project) {
            const role = this.user?.role;
            if (!role) return false;
            const s = project.status;
            
            if (role === 'teacher') return ['midterm_submitted', 'conclusion_submitted'].includes(s);
            if (role === 'college_approver') return ['midterm_advisor_approved', 'conclusion_advisor_approved'].includes(s);
            if (role === 'school_approver') return ['midterm_college_approved', 'conclusion_college_approved'].includes(s);
            
            return false;
        },
        canUploadFile(project) {
            // 学生或项目管理员，且是该项目的负责人(简化判断：只要是student/project_admin角色)
            // 实际上应该判断是否是该项目成员，但这里简化为角色判断+状态
            const isStudent = this.user?.role === 'student' || this.user?.role === 'project_admin';
            // 状态为 'rated' (立项后，可交中期) 或 'midterm_approved' (中期通过后，可交结项)
            // 或者是被驳回的状态，也可以重新提交
            return isStudent && ['rated', 'midterm_approved', 'midterm_rejected', 'conclusion_rejected'].includes(project.status);
        },
        canReview(project) {
            return this.user?.role === 'judge' && ['school_approved', 'rated'].includes(project.status);
        },

        // --- Actions ---
        async markAsRead(row) {
            try {
                await axios.put(`/api/notifications/${row.id}/read`);
                row.is_read = 1;
            } catch(e) {}
        },
        async updateProfile() {
            this.savingProfile = true;
            try {
                await axios.put('/api/me', this.profileForm);
                ElementPlus.ElMessage.success('个人信息更新成功');
                const res = await axios.get('/api/me');
                this.user = res.data;
            } catch(e) {
                ElementPlus.ElMessage.error(e.response?.data?.error || '更新失败');
            } finally {
                this.savingProfile = false;
            }
        },
        async changePassword() {
            if (this.passwordForm.new_password !== this.passwordForm.confirm_password) {
                ElementPlus.ElMessage.warning('两次输入的新密码不一致');
                return;
            }
            this.changingPassword = true;
            try {
                await axios.put('/api/me/password', {
                    old_password: this.passwordForm.old_password,
                    new_password: this.passwordForm.new_password
                });
                ElementPlus.ElMessage.success('密码修改成功，请重新登录');
                setTimeout(() => {
                    this.logout();
                }, 1500);
            } catch(e) {
                ElementPlus.ElMessage.error(e.response?.data?.error || '修改失败');
            } finally {
                this.changingPassword = false;
            }
        },
        async backupSystem() {
            this.backupLoading = true;
            try {
                const res = await axios.post('/api/system/backup');
                ElementPlus.ElMessage.success(res.data.message || '备份成功');
                if (res.data && res.data.path) {
                    window.open(res.data.path, '_blank');
                }
            } catch(e) { 
                ElementPlus.ElMessage.error(e.response?.data?.error || '备份失败'); 
            }
            finally { this.backupLoading = false; }
        },

        async createAnnouncement() {
            if (!this.announcementForm.title || !this.announcementForm.content) {
                ElementPlus.ElMessage.warning('请填写标题和内容');
                return;
            }
            try {
                await axios.post('/api/announcements', this.announcementForm);
                ElementPlus.ElMessage.success('发布成功');
                this.showAnnouncementDialog = false;
                this.announcementForm = { title: '', content: '', type: 'news' };
                this.fetchAnnouncements();
                // Check for new notifications immediately after publishing
                setTimeout(() => this.checkNewNotifications(), 500); 
            } catch(e) { 
                console.error(e);
                ElementPlus.ElMessage.error(e.response?.data?.error || '发布失败'); 
            }
        },
        async deleteAnnouncement(id) {
            try {
                await ElementPlus.ElMessageBox.confirm('确定删除该公告吗？', '提示', { type: 'warning' });
                await axios.delete(`/api/announcements/${id}`);
                ElementPlus.ElMessage.success('删除成功');
                this.fetchAnnouncements();
            } catch(e) {}
        },

        getFieldValue(form, key) {
            // Helper to get value from nested object using dot notation
            return key.split('.').reduce((obj, i) => obj ? obj[i] : null, form);
        },
        openCreateDialog() {
            console.log('DEBUG: openCreateDialog called');
            this.isEditing = false;
            this.currentEditingId = null;
            this.showCreateDialog = true;
            this.activeStep = 0;
            
            const leaderInfo = {};
            if (this.user?.role === 'student') {
                 leaderInfo.name = this.user.real_name;
                 leaderInfo.id = this.user.identity_number;
                 leaderInfo.college = this.user.college;
            }

            this.createForm = {
                id: undefined, // Explicitly reset ID
                title: '', project_type: 'innovation', level: 'school', year: '2025',
                leader_name: this.user?.real_name || '', advisor_name: '', 
                inspiration_source: '', // Initialize inspiration source
                members: [],
                template_type: 'default',
                extra_info: {
                    leader_info: leaderInfo
                },
                form_config: {
                    show_company_info: true,
                    show_advisor: true,
                    show_team_members: false,
                    show_attachments: true
                }
            };
            console.log('DEBUG: openCreateDialog reset createForm.id to undefined');
        },
        addMember() { 
            const leaderCollege = this.createForm.extra_info?.leader_info?.college || this.createForm.college || '';
            this.createForm.members.push({
                name: '',
                student_id: '',
                college: leaderCollege,
                degree: '',
                major: '',
                phone: '',
                email: '',
                year: '',
                grad_year: ''
            }); 
        },
        removeMember(index) {
            this.createForm.members.splice(index, 1);
        },
        nextStep() { this.activeStep++; },
        
        async submitProject() {
            if (this.submitting) return; // Prevent double submission
            console.log('DEBUG: submitProject called');
            console.log('DEBUG: isEditing:', this.isEditing);
            console.log('DEBUG: createForm.id:', this.createForm.id);
            console.log('DEBUG: createForm full:', JSON.parse(JSON.stringify(this.createForm)));

            // Ghost ID Detection & Recovery
            if ([6, 7, 8, 9].includes(Number(this.createForm.id))) {
                 console.error(`CRITICAL: submitProject found Ghost ID (${this.createForm.id})! Checking recovery options...`);
                 
                 // Try to recover from currentEditingId (RELAXED CHECK)
                 if (this.currentEditingId && ![6, 7, 8, 9].includes(Number(this.currentEditingId))) {
                     console.warn(`RECOVERY: Overwriting Ghost ID ${this.createForm.id} with Backup ID ${this.currentEditingId}`);
                     this.createForm.id = this.currentEditingId;
                     // Continue execution with restored ID
                 } else {
                     // Try Title Match Recovery
                     const match = this.projects.find(p => p.title === this.createForm.title && ![6, 7, 8, 9].includes(Number(p.id)));
                     if (match) {
                         console.warn(`RECOVERY: Overwriting Ghost ID ${this.createForm.id} with Title Match ID ${match.id}`);
                         this.createForm.id = match.id;
                         this.currentEditingId = match.id;
                     } else {
                         console.error('FATAL: Could not recover from Ghost ID. Aborting.');
                         alert(`CRITICAL ERROR: Detected Ghost ID (${this.createForm.id}). Recovery failed. Debug: isEditing=${this.isEditing}, currentEditingId=${this.currentEditingId}`);
                         this.submitting = false;
                         return; // Stop execution
                     }
                 }
            }

            // Robustness: Force isEditing if ID is clearly present
            if (!this.isEditing && this.createForm.id && !isNaN(Number(this.createForm.id)) && Number(this.createForm.id) > 0) {
                console.warn('DEBUG: Forced isEditing to true because ID exists');
                this.isEditing = true;
            }

            // Sync leader info from extra_info to root fields for backend storage
            if (this.createForm.template_type === 'startup' && this.createForm.extra_info?.leader_info) {
                const l = this.createForm.extra_info.leader_info;
                this.createForm.leader_name = l.name;
                this.createForm.leader_id = l.id; // Mapping for backend
                this.createForm.student_id = l.id;
                this.createForm.college = l.college;
                this.createForm.major = l.major;
                this.createForm.contact = l.email || l.phone;
            }

            // Validation
            if (this.createForm.template_type === 'startup') {
                if (!this.createForm.title) {
                    ElementPlus.ElMessage.warning('请输入项目名称'); return;
                }
                if (!this.createForm.extra_info?.attachments?.business_plan) {
                     ElementPlus.ElMessage.warning('请上传商业计划书'); return;
                }
                
                // 评审阶段必须上传路演材料
                if (this.createForm.status === 'school_approved') {
                     if (!this.createForm.extra_info?.attachments?.pitch_ppt) {
                         ElementPlus.ElMessage.warning('进入评审阶段后，必须上传路演PPT'); return;
                     }
                     if (!this.createForm.extra_info?.attachments?.pitch_video) {
                         ElementPlus.ElMessage.warning('进入评审阶段后，必须上传路演视频'); return;
                     }
                }
            } else {
                 if (!this.createForm.title) {
                    ElementPlus.ElMessage.warning('请输入项目名称'); return;
                }
            }

            this.submitting = true;
            try {
                const payload = JSON.parse(JSON.stringify(this.createForm));
                if (payload.template_type === 'startup' && Array.isArray(payload.members)) {
                    payload.members = payload.members.slice(1);
                }

                // --- STRICT ID ENFORCEMENT START ---
                // We rely exclusively on currentEditingId to determine the target ID.
                // This neutralizes any "Ghost IDs" (6, 7, 8...) that might appear in createForm.id
                
                if (this.currentEditingId) {
                    // SAFETY CHECK: Block Ghost IDs in currentEditingId
                    if ([6, 7, 8, 9].includes(Number(this.currentEditingId))) {
                        console.error(`CRITICAL: currentEditingId is Ghost ID (${this.currentEditingId}) in submitProject! Aborting.`);
                        ElementPlus.ElMessage.error('系统检测到无效的项目ID，无法提交。请刷新页面。');
                        this.submitting = false;
                        return;
                    }

                    // EDIT MODE: Force payload to use the trusted backup ID
                    if (String(payload.id) !== String(this.currentEditingId)) {
                        console.warn(`CRITICAL: ID Mismatch in Edit Mode! createForm.id=${payload.id}, currentEditingId=${this.currentEditingId}. Enforcing currentEditingId.`);
                    }
                    payload.id = this.currentEditingId;
                    this.createForm.id = this.currentEditingId; 
                    this.isEditing = true;
                } else {
                    // CREATE MODE: Force removal of any ID to prevent accidental PUTs to Ghost IDs
                    if (payload.id) {
                        console.warn(`CRITICAL: Ghost ID detected in Create Mode! createForm.id=${payload.id}. Removing it to ensure POST.`);
                        payload.id = undefined;
                        this.createForm.id = undefined;
                    }
                    this.isEditing = false;
                }
                // --- STRICT ID ENFORCEMENT END ---

                if (this.isEditing) {
                    // Ensure ID is a clean integer for the URL
                    const cleanId = parseInt(payload.id, 10);
                    console.log(`DEBUG: Executing PUT /api/projects/${cleanId}`);
                    await axios.put(`/api/projects/${cleanId}`, payload);
                    ElementPlus.ElMessage.success('项目修改提交成功');
                } else {
                    // Create New Project
                    // Double check we are not sending an ID
                    if (payload.id) delete payload.id;
                    
                    // TWIN PROJECT DETECTION
                        // Check if a project with the same title already exists for this user.
                        // This helps detect cases where 'isEditing' state was lost but form data remained.
                        if (this.user?.role === 'student') {
                            const duplicate = this.projects.find(p => p.title === payload.title);
                            if (duplicate) {
                                console.error(`POTENTIAL TWIN PROJECT DETECTED: Creating new project with title '${payload.title}' but it already exists (ID ${duplicate.id}).`);
                                // We cannot block this safely without risking false positives, but we log it.
                            }
                        }

                        const resp = await axios.post('/api/projects', payload);
                        const newId = resp?.data?.project_id;
                        ElementPlus.ElMessage.success('申请提交成功');
                        if (newId && !isNaN(Number(newId)) && Number(newId) > 0) {
                            try {
                                await this.viewDetails(Number(newId));
                                if (this.currentProject) {
                                    this.projects = Array.isArray(this.projects) ? this.projects : [];
                                    const existsIdx = this.projects.findIndex(p => Number(p.id) === Number(newId));
                                    if (existsIdx >= 0) {
                                        this.projects.splice(existsIdx, 1, this.currentProject);
                                    } else {
                                        this.projects.unshift(this.currentProject);
                                    }
                                }
                            } catch(e) {}
                        }
                    }
                this.fetchNotifications();
                if (this.isEditing && this.createForm?.id) {
                    await this.viewDetails(this.createForm.id);
                    const idx = this.projects.findIndex(p => Number(p.id) === Number(this.createForm.id));
                    if (idx >= 0 && this.currentProject) {
                        this.projects.splice(idx, 1, this.currentProject);
                    }
                }
                this.showCreateDialog = false;
                this.fetchProjects();
                this.fetchCompetitions(); // 刷新赛事状态
                // Explicitly reset createForm to avoid state leakage
                this.createForm = { id: undefined, title: '', project_type: 'innovation', members: [] }; 
                this.isEditing = false;
            } catch (error) {
                if (error.response && error.response.status === 404) {
                    const reqUrl = error.response.config.url;
                    const reqMethod = error.response.config.method;
                    const reqData = error.response.config.data ? JSON.parse(error.response.config.data) : {};
                    const id = reqData.id || 'unknown';
                    ElementPlus.ElMessage.error(`项目不存在(404)。请求: ${reqMethod} ${reqUrl}, ID: ${id}`);
                    console.error(`404 Error Detail: URL=${reqUrl}, Method=${reqMethod}, ID=${id}`);
                    this.showCreateDialog = false;
                    this.fetchProjects();
                } else {
                    ElementPlus.ElMessage.error(error.response?.data?.error || '操作失败');
                }
            } finally {
                this.submitting = false;
            }
        },
        
        // --- Consistency Helpers ---
        syncCompetitionProjectMapping() {
            try {
                const validIds = new Set(
                    (Array.isArray(this.projects) ? this.projects : [])
                        .map(p => Number(p?.id))
                        .filter(id => !isNaN(id) && id > 0)
                );
                console.log('DEBUG: syncCompetitionProjectMapping validIds:', Array.from(validIds));
                this.competitions = (Array.isArray(this.competitions) ? this.competitions : []).map(c => {
                    if (c && c.is_registered) {
                        const pid = Number(c.project_id);
                        console.log(`DEBUG: Checking comp ${c.id} project_id ${pid}`);
                        if (isNaN(pid) || pid <= 0 || [6, 7, 8, 9].includes(pid) || !validIds.has(pid)) {
                            console.warn(`DEBUG: Removing invalid project_id ${pid} from comp ${c.id}`);
                            return { ...c, is_registered: false, project_id: null, project_status: null };
                        }
                    }
                    return c;
                });
            } catch(e) { console.error('DEBUG: sync error', e); }
        },

        // --- Competition Management ---
        openCompDialog(comp) {
            this.showCompDialog = true;
            if (comp) {
                this.isEditingComp = true;
                this.compForm = { ...comp };
                // Ensure form_config exists
                if (!this.compForm.form_config) {
                    this.compForm.form_config = {
                        show_company_info: false,
                        show_advisor: true,
                        show_team_members: false,
                        show_attachments: true,
                        batch_type: 'program',
                        allowed_project_types: ['innovation', 'entrepreneurship_training', 'entrepreneurship_practice']
                    };
                } else if (typeof this.compForm.form_config === 'string') {
                    try {
                        this.compForm.form_config = JSON.parse(this.compForm.form_config);
                    } catch(e) {
                        this.compForm.form_config = {
                            show_company_info: false,
                            show_advisor: true,
                            show_team_members: false,
                            show_attachments: true,
                            batch_type: 'program',
                            allowed_project_types: ['innovation', 'entrepreneurship_training', 'entrepreneurship_practice']
                        };
                    }
                }
                // Ensure new fields exist for legacy data
                if (!this.compForm.form_config.batch_type) this.compForm.form_config.batch_type = 'program';
                if (!this.compForm.form_config.allowed_project_types) this.compForm.form_config.allowed_project_types = ['innovation', 'entrepreneurship_training', 'entrepreneurship_practice'];
            } else {
                this.isEditingComp = false;
                this.compForm = { 
                    title: '', level: 'School', organizer: '', registration_start: '', registration_end: '', status: 'active', 
                    template_type: 'default',
                    form_config: {
                        show_company_info: false,
                        show_advisor: true,
                        show_team_members: false,
                        show_attachments: true,
                        batch_type: 'program',
                        allowed_project_types: ['innovation', 'entrepreneurship_training', 'entrepreneurship_practice']
                    }
                };
            }
        },
        openFormDesigner() {
            // Initialize with current config or default
            if (!this.compForm.form_config.groups || this.compForm.form_config.groups.length === 0) {
                 this.currentFormConfig = {
                     groups: [
                         {
                             title: '项目基本信息',
                             fields: [
                                 { key: 'title', label: '项目名称', type: 'text', required: true, system: true },
                                 { key: 'project_type', label: '项目类别', type: 'select', required: true, system: true, options: [] },
                                 { key: 'level', label: '项目级别', type: 'select', required: true, system: true, options: [ {label:'校级',value:'school'}, {label:'省级',value:'provincial'}, {label:'国家级',value:'national'} ] },
                                 { key: 'college', label: '所在院系', type: 'select', required: true, system: true, options: [] },
                                 { key: 'year', label: '年份', type: 'text', required: true, system: true },
                                 { key: 'leader_name', label: '负责人', type: 'text', required: true, system: true, disabled: true },
                                 { key: 'advisor_name', label: '指导老师', type: 'text', required: true, system: true }
                             ]
                         }
                     ]
                 };
            } else {
                this.currentFormConfig = JSON.parse(JSON.stringify(this.compForm.form_config));
            }
            this.showFormDesignerDialog = true;
        },
        saveFormConfig() {
            this.compForm.form_config = {
                ...this.compForm.form_config,
                groups: this.currentFormConfig.groups
            };
            this.showFormDesignerDialog = false;
            ElementPlus.ElMessage.success('表单配置已更新');
        },
        applyPreset(val) {
            if (!val) return;
            const preset = this.presetTemplates.find(p => p.value === val);
            if (preset) {
                // Merge preset data into compForm
                this.compForm.title = preset.data.title;
                this.compForm.level = preset.data.level;
                this.compForm.template_type = preset.data.template_type;
                this.compForm.organizer = preset.data.organizer;
                
                // Deep merge form_config
                this.compForm.form_config = {
                    ...this.compForm.form_config,
                    ...preset.data.form_config
                };
                
                ElementPlus.ElMessage.success('已应用模板：' + preset.label);
            }
        },
        async saveCompetition() {
            if (!this.compForm.title) {
                ElementPlus.ElMessage.warning('请输入赛事名称');
                return;
            }
            try {
                if (this.isEditingComp) {
                    await axios.put(`/api/competitions/${this.compForm.id}`, this.compForm);
                    ElementPlus.ElMessage.success('更新成功');
                } else {
                    await axios.post('/api/competitions', this.compForm);
                    ElementPlus.ElMessage.success('发布成功');
                }
                this.showCompDialog = false;
                this.fetchCompetitions();
            } catch(e) { 
                console.error(e);
                ElementPlus.ElMessage.error(e.response?.data?.error || '操作失败'); 
            }
        },
        async deleteCompetition(id) {
            try {
                await ElementPlus.ElMessageBox.confirm('确定删除该赛事吗？', '提示', { type: 'warning' });
                await axios.delete(`/api/competitions/${id}`);
                ElementPlus.ElMessage.success('删除成功');
                this.fetchCompetitions();
            } catch(e) {}
        },
        applyCompetition(comp) {
            console.log('DEBUG: applyCompetition called with:', comp);
            this.openCreateDialog();
            this.createForm.competition_id = comp.id;
            // Explicitly ensure ID is undefined for new application
            this.createForm.id = undefined;
            this.createForm.template_type = comp.template_type || 'default'; // 设置模板类型
            this.createForm.title = comp.title + ' - 参赛项目';
            
            if (comp.form_config) {
                try {
                    this.createForm.form_config = (typeof comp.form_config === 'string') ? JSON.parse(comp.form_config) : comp.form_config;
                } catch(e) {
                    console.error("Error parsing form_config", e);
                }
            }

            // 初始化 Template 2 的 extra_info
            if (this.createForm.template_type === 'startup') {
                const currentLeaderInfo = this.createForm.extra_info?.leader_info || {};
                this.createForm.project_type = 'entrepreneurship_training';
                this.createForm.extra_info = {
                    company_info: {
                        legal_rep: {},
                        shareholders: [],
                        investments: []
                    },
                    advisor_info: {},
                    leader_info: currentLeaderInfo,
                    attachments: {}
                };
            } else {
                 // Check allowed project types for default template
                 const allowed = this.createForm.form_config?.allowed_project_types;
                 if (allowed && Array.isArray(allowed) && allowed.length > 0) {
                     if (!allowed.includes(this.createForm.project_type)) {
                         this.createForm.project_type = allowed[0];
                     }
                 }
            }
        },

        async viewDetails(id) {
            console.log('DEBUG: viewDetails called with ID:', id);
            try {
                if (id === undefined || id === null || isNaN(Number(id)) || Number(id) <= 0) {
                    ElementPlus.ElMessage.warning('项目ID缺失或无效，请刷新列表后重试');
                    await this.fetchProjects();
                    await this.fetchCompetitions();
                    return;
                }
                const cleanId = parseInt(id, 10);
                console.log(`DEBUG: Fetching details for ID ${cleanId}`);
                const res = await axios.get(`/api/projects/${cleanId}?t=${new Date().getTime()}`);
                
                console.log('DEBUG: Detail response:', res.data);
                if (res.data.id !== cleanId) {
                    console.error(`CRITICAL: Requested ID ${cleanId} but got ID ${res.data.id}`);
                    ElementPlus.ElMessage.error(`数据异常：请求项目 ${cleanId} 但返回了 ${res.data.id}`);
                }
                
                this.currentProject = res.data;
                console.log('DEBUG: this.currentProject set to:', this.currentProject);

                let tpl = 'default';
                if (this.currentProject.competition_id) {
                    const compId = Number(this.currentProject.competition_id);
                    let comp = this.competitions.find(c => Number(c.id) === compId);
                    if (!comp) {
                        try {
                            const compsRes = await axios.get('/api/competitions');
                            this.competitions = compsRes.data;
                            comp = this.competitions.find(c => Number(c.id) === compId);
                        } catch(e) {}
                    }
                    if (comp && comp.template_type) tpl = comp.template_type;
                }
                const info = this.currentProject?.extra_info || {};
                if (tpl === 'default' && (info.company_info || info.leader_info || info.attachments)) {
                    tpl = 'startup';
                }
                this.currentProject.template_type = tpl;

                this.detailActiveTab = 'basic';
                this.isAuditing = false;
                this.showDetailDialog = true;
            } catch(e) { 
                const msg = (e && e.response && e.response.status === 404) ? '项目不存在或已被删除' : '获取详情失败';
                ElementPlus.ElMessage.error(msg); 
                this.showDetailDialog = false;
                if (id) {
                    const idx = this.projects.findIndex(p => p.id === id);
                    if (idx >= 0) this.projects.splice(idx, 1);
                }
                this.fetchProjects();
                this.fetchCompetitions();
                throw e;
            }
        },
        async openAuditDialog(project, action) {
            console.log('DEBUG: openAuditDialog called with:', project, action);
            try {
                if (!project || !project.id) {
                    ElementPlus.ElMessage.warning('项目ID缺失，请刷新列表后重试');
                    await this.fetchProjects();
                    return;
                }
                await this.viewDetails(project.id);

                this.isAuditing = true;
                this.detailActiveTab = 'audit';
                this.auditAction = action;
                this.auditFeedback = '';
                this.auditLevel = ''; // Reset
                this.auditGrade = ''; // Reset
                this.showDetailDialog = true;
            } catch(e) {
                console.error("Audit dialog open failed:", e);
            }
        },
        async confirmAudit() {
            console.log('DEBUG: confirmAudit called for ID:', this.currentProject?.id);
            if (this.currentProject?.id == 6 || this.currentProject?.id == '6') {
                 console.error('CRITICAL: confirmAudit found ID 6! Stack trace:', new Error().stack);
            }

            if (this.auditAction === 'reject' && !this.auditFeedback) {
                ElementPlus.ElMessage.warning('驳回必须填写理由');
                return;
            }
            // Validation for new fields
            if (this.auditAction === 'approve') {
                if (this.currentProject.status === 'under_review' && !this.auditLevel) {
                     ElementPlus.ElMessage.warning('请选择项目级别');
                     return;
                }
                if (this.currentProject.status === 'under_final_review' && !this.auditGrade) {
                     ElementPlus.ElMessage.warning('请评定成绩');
                     return;
                }
            }
            
            if (!this.currentProject || !this.currentProject.id) {
                 ElementPlus.ElMessage.error('审批失败：项目ID丢失，请刷新重试');
                 return;
            }
            this.submitting = true;
            try {
                await axios.put(`/api/projects/${parseInt(this.currentProject.id, 10)}/audit`, {
                    action: this.auditAction,
                    feedback: this.auditFeedback,
                    project_level: this.auditLevel,
                    final_grade: this.auditGrade
                });
                ElementPlus.ElMessage.success('审批成功');
                this.fetchNotifications();
                this.showDetailDialog = false;
                this.fetchProjects();
            } catch(e) { 
                const msg = (e && e.response && e.response.status === 404) ? '项目不存在或已被删除' : (e.response?.data?.error || '失败');
                ElementPlus.ElMessage.error(msg); 
                this.showDetailDialog = false;
                if (this.currentProject && this.currentProject.id) {
                    const idx = this.projects.findIndex(p => p.id === this.currentProject.id);
                    if (idx >= 0) this.projects.splice(idx, 1);
                }
                this.fetchProjects();
                this.fetchCompetitions();
            }
            finally { this.submitting = false; }
        },

        openReviewDialog(project) {
            this.currentProject = project;
            this.reviewForm = { score: 80, comment: '' };
            this.showReviewDialog = true;
        },
        async submitReview() {
            this.submitting = true;
            try {
                if (!this.currentProject || !this.currentProject.id) {
                    this.submitting = false;
                    console.error('Project ID missing:', this.currentProject);
                    ElementPlus.ElMessage.error('无法提交：项目ID丢失，请刷新页面重试');
                    return;
                }

                if (!this.reviewForm.comment || this.reviewForm.comment.trim() === '') {
                    this.submitting = false;
                    ElementPlus.ElMessage.warning('请填写评语');
                    return;
                }
                
                const url = `/api/projects/${parseInt(this.currentProject.id, 10)}/review`;
                console.log('Submitting review to:', url, this.reviewForm);

                await axios.post(url, this.reviewForm);
                ElementPlus.ElMessage.success('评审提交成功');
                this.showReviewDialog = false;
                this.fetchProjects();
            } catch(e) { 
                console.error('Review submission error:', e);
                const msg = e.response?.data?.error 
                    || (typeof e.response?.data === 'string' ? e.response.data : e.message || '失败');
                ElementPlus.ElMessage.error(msg); 
            }
            finally { this.submitting = false; }
        },

        // File Upload Helpers
        handleFileUpload(event, path) {
            const file = event.target.files[0];
            if (!file) return;
            
            // CRITICAL CHECK FOR GHOST ID
            if (this.createForm && [6, 7, 8, 9].includes(Number(this.createForm.id))) {
                 console.error(`CRITICAL: handleFileUpload detected Ghost ID (${this.createForm.id})! Stack trace:`, new Error().stack);
                 alert(`CRITICAL ERROR: Detected Ghost ID (${this.createForm.id}) during file upload. Stop.`);
                 return;
            }

            if (file.size > 25 * 1024 * 1024) { // Max 25MB as per requirement (video)
                ElementPlus.ElMessage.warning('文件大小不能超过25MB');
                return;
            }

            const formData = new FormData();
            formData.append('file', file);

            axios.post('/api/common/upload', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            }).then(res => {
                const parts = path.split('.');
                let obj = this.createForm;
                for (let i = 0; i < parts.length - 1; i++) {
                    if (!obj[parts[i]]) obj[parts[i]] = {};
                    obj = obj[parts[i]];
                }
                obj[parts[parts.length - 1]] = res.data.url;
                
                // 同步到详情弹窗的 currentProject（如果正在查看同一项目）
                if (this.showDetailDialog && this.currentProject && this.currentProject.id === this.createForm.id) {
                    let target = this.currentProject;
                    for (let i = 0; i < parts.length - 1; i++) {
                        // 如果中间层不存在，则创建对象以保证赋值成功
                        if (!target[parts[i]]) target[parts[i]] = {};
                        target = target[parts[i]];
                    }
                    target[parts[parts.length - 1]] = res.data.url;
                }
                
                ElementPlus.ElMessage.success('上传成功');
                
                // Auto-save when editing an existing project
                if (this.isEditing && this.createForm?.id) {
                    const cleanId = parseInt(this.createForm.id, 10);
                    axios.put(`/api/projects/${cleanId}`, this.createForm)
                        .then(() => {
                            ElementPlus.ElMessage.success('附件已自动保存');
                            // Refresh project list to reflect saved state，但不自动弹出详情
                            this.fetchProjects();
                        })
                        .catch(err => {
                            if (err.response && err.response.status === 404) {
                                ElementPlus.ElMessage.error('自动保存失败：项目不存在或已被删除');
                                this.fetchProjects();
                            } else {
                                ElementPlus.ElMessage.error(err.response?.data?.error || '自动保存失败，请稍后重试');
                            }
                        });
                }
            }).catch(err => {
                ElementPlus.ElMessage.error('上传失败');
            });
        },
        addShareholder() {
            if (!this.createForm.extra_info.company_info.shareholders) this.createForm.extra_info.company_info.shareholders = [];
            this.createForm.extra_info.company_info.shareholders.push({});
        },
        removeShareholder(i) {
            this.createForm.extra_info.company_info.shareholders.splice(i, 1);
        },
        addInvestment() {
            if (!this.createForm.extra_info.company_info.investments) this.createForm.extra_info.company_info.investments = [];
            this.createForm.extra_info.company_info.investments.push({});
        },
        removeInvestment(i) {
            this.createForm.extra_info.company_info.investments.splice(i, 1);
        },

        async editProject(row) {
            console.log('DEBUG: editProject called with:', JSON.parse(JSON.stringify(row)));
            if (row && [6, 7, 8, 9].includes(Number(row.id))) {
                 console.error(`CRITICAL: editProject blocked for Ghost ID ${row.id}!`);
                 ElementPlus.ElMessage.error('该项目不存在或已被删除，请刷新页面。');
                 await this.fetchProjects(); // Force refresh to remove it from UI
                 return;
            }
            if (row && (row.id == 6 || row.id == '6' || row.id == 7 || row.id == '7')) {
                 console.error('CRITICAL: editProject found Ghost ID (6 or 7)! Stack trace:', new Error().stack);
                 alert('CRITICAL ERROR: Detected Ghost ID (6 or 7) in editProject. Please report this.');
                 return;
            }
            console.log('DEBUG: editProject row.id:', row ? row.id : 'undefined');
            if (row) {
                console.log('DEBUG: editProject row type:', typeof row.id);
            }
            try {
                if (!row || row.id === undefined || row.id === null || isNaN(Number(row.id)) || Number(row.id) <= 0) {
                    ElementPlus.ElMessage.warning('项目ID缺失或无效，请刷新列表后重试');
                    await this.fetchProjects();
                    return;
                }
            } catch(_) {}
            try {
                const cleanId = parseInt(row.id, 10);
                console.log(`DEBUG: Fetching project detail for edit: ID=${cleanId}`);
                const res = await axios.get(`/api/projects/${cleanId}?t=${new Date().getTime()}`);
                const project = res.data;
                console.log('DEBUG: Fetched project detail:', project);
                
                this.isEditing = true;
                this.currentEditingId = project.id; // Backup ID
                this.showCreateDialog = true;
                this.activeStep = 0;
                
                // Determine template type
                let template_type = 'default';
                let form_config = {
                    show_company_info: false,
                    show_advisor: true,
                    show_team_members: false,
                    show_attachments: true
                };
                if (project.competition_id) {
                    const compId = Number(project.competition_id);
                    let comp = this.competitions.find(c => Number(c.id) === compId);
                    if (!comp) {
                        try {
                            const compsRes = await axios.get('/api/competitions');
                            this.competitions = compsRes.data;
                            comp = this.competitions.find(c => Number(c.id) === compId);
                        } catch(e) {}
                    }
                    if (comp) {
                        template_type = comp.template_type;
                        // Merge form_config from competition (if exists)
                        if (comp.form_config) {
                            try {
                                const cfg = typeof comp.form_config === 'string' ? JSON.parse(comp.form_config) : comp.form_config;
                                form_config = {
                                    show_company_info: cfg.show_company_info ?? false,
                                    show_advisor: cfg.show_advisor ?? true,
                                    show_team_members: cfg.show_team_members ?? false,
                                    show_attachments: cfg.show_attachments ?? true
                                };
                            } catch(e) {
                                // keep defaults
                            }
                        }
                    }
                }
                if (template_type === 'default') {
                    const info = project?.extra_info || {};
                    if (info.company_info || info.leader_info || info.attachments) {
                        template_type = 'startup';
                    }
                }
                
                // Populate createForm
                this.createForm = {
                    id: project.id,
                    status: project.status,
                    title: project.title,
                    project_type: project.project_type,
                    level: project.level,
                    year: project.year,
                    leader_name: project.leader_name,
                    advisor_name: project.advisor_name,
                    department: project.department,
                    college: project.college,
                    abstract: project.abstract,
                    assessment_indicators: project.assessment_indicators,
                    competition_id: project.competition_id,
                    template_type: template_type,
                    form_config: form_config,
                    extra_info: JSON.parse(JSON.stringify(project.extra_info || {})),
                    
                    // Extended fields
                    background: project.background,
                    content: project.content,
                    innovation_point: project.innovation_point,
                    expected_result: project.expected_result,
                    budget: project.budget,
                    schedule: project.schedule,
                    source: project.project_source, 
                    risk_control: project.risk_control,
                    
                    team_intro: project.team_intro,
                    market_prospect: project.market_prospect,
                    operation_mode: project.operation_mode,
                    financial_budget: project.financial_budget,
                    risk_budget: project.risk_budget,
                    investment_budget: project.investment_budget,
                    tech_maturity: project.tech_maturity,
                    enterprise_mentor: project.enterprise_mentor,
                    innovation_content: project.innovation_content,
                    
                    members: project.members.filter(m => !m.is_leader)
                };
                if (!this.createForm.extra_info) this.createForm.extra_info = {};
                if (!this.createForm.extra_info.attachments) this.createForm.extra_info.attachments = {};
                
                // Ensure nested objects exist for startup template
                if (template_type === 'startup') {
                    if (!this.createForm.extra_info.company_info) this.createForm.extra_info.company_info = {};
                    if (!this.createForm.extra_info.company_info.legal_rep) this.createForm.extra_info.company_info.legal_rep = {};
                    if (!this.createForm.extra_info.company_info.shareholders) this.createForm.extra_info.company_info.shareholders = [];
                    if (!this.createForm.extra_info.company_info.investments) this.createForm.extra_info.company_info.investments = [];
                    if (!this.createForm.extra_info.advisor_info) this.createForm.extra_info.advisor_info = {};
                    if (!this.createForm.extra_info.leader_info) this.createForm.extra_info.leader_info = {};
                    if (!this.createForm.extra_info.attachments) this.createForm.extra_info.attachments = {};
                    const l = this.createForm.extra_info.leader_info || {};
                    const leaderMember = {
                        name: l.name || this.createForm.leader_name || '',
                        student_id: l.id || this.createForm.student_id || '',
                        college: l.college || this.createForm.college || '',
                        major: l.major || '',
                        degree: l.degree || '',
                        year: l.year || '',
                        grad_year: l.grad_year || '',
                        phone: l.phone || '',
                        email: l.email || ''
                    };
                    if (!Array.isArray(this.createForm.members)) this.createForm.members = [];
                    this.createForm.members.unshift(leaderMember);
                }
                
            } catch(e) {
                const msg = (e && e.response && e.response.status === 404) ? '项目不存在或已被删除' : '获取项目详情失败';
                ElementPlus.ElMessage.error(msg);
                if (row && row.id) {
                    const idx = this.projects.findIndex(p => p.id === row.id);
                    if (idx >= 0) this.projects.splice(idx, 1);
                }
                this.fetchProjects();
                return false;
            }
            return true;
        },

        openUploadDialog(type) {
            this.uploadForm = { file_type: type, file_name: '' };
            this.showUploadDialog = true;
        },
        openUploadDialogWithProject(project, type) {
            this.currentProject = project;
            this.openUploadDialog(type);
        },
        async openPitchUploadWithProject(project) {
            try {
                if (!project || !project.id) {
                    ElementPlus.ElMessage.warning('项目ID缺失，请刷新列表后重试');
                    await this.fetchProjects();
                    return;
                }
                await this.editProject(project);
                const compId = Number(project.competition_id);
                let comp = this.competitions.find(c => Number(c.id) === compId);
                if (!comp) {
                    try {
                        const compsRes = await axios.get('/api/competitions');
                        this.competitions = compsRes.data;
                        comp = this.competitions.find(c => Number(c.id) === compId);
                    } catch(e) {}
                }
                const tpl = comp && comp.template_type ? comp.template_type : 'default';
                if (tpl !== 'startup') {
                    ElementPlus.ElMessage.info('该项目模板无需上传路演材料');
                    return;
                }
                this.activeStep = 1;
                // ElementPlus.ElMessage.info('请在该页面上传路演PPT与视频');
            } catch(e) {
                ElementPlus.ElMessage.error('打开上传入口失败');
            }
        },
        async openBusinessPlanUploadWithProject(project) {
            try {
                if (!project || !project.id) {
                    ElementPlus.ElMessage.warning('项目ID缺失，请刷新列表后重试');
                    await this.fetchProjects();
                    return;
                }
                await this.editProject(project);
                const compId = Number(project.competition_id);
                let comp = this.competitions.find(c => Number(c.id) === compId);
                if (!comp) {
                    try {
                        const compsRes = await axios.get('/api/competitions');
                        this.competitions = compsRes.data;
                        comp = this.competitions.find(c => Number(c.id) === compId);
                    } catch(e) {}
                }
                const tpl = comp && comp.template_type ? comp.template_type : 'default';
                if (tpl !== 'startup') {
                    ElementPlus.ElMessage.info('该项目模板无需上传商业计划书');
                    return;
                }
                this.activeStep = 1;
            } catch(e) {
                ElementPlus.ElMessage.error('打开上传入口失败');
            }
        },
        async submitUpload() {
            if (!this.uploadForm.file_name) return ElementPlus.ElMessage.warning('请输入文件名');
            this.submitting = true;
            try {
                await axios.post(`/api/projects/${parseInt(this.currentProject.id, 10)}/files`, this.uploadForm);
                ElementPlus.ElMessage.success('提交成功');
                this.fetchNotifications();
                this.showUploadDialog = false;
                this.viewDetails(this.currentProject.id); // refresh details
                this.fetchProjects(); // refresh list status
            } catch(e) {
                ElementPlus.ElMessage.error(e.response?.data?.error || '失败');
            } finally {
                this.submitting = false;
            }
        },
        async auditFile(type, action) {
            if (action === 'reject' && !this.fileAuditFeedback) {
                ElementPlus.ElMessage.warning('驳回时请填写审核意见');
                return;
            }
            try {
                // Reuse the main audit endpoint which handles status transitions based on current status
                await axios.put(`/api/projects/${parseInt(this.currentProject.id, 10)}/audit`, { 
                    action,
                    feedback: this.fileAuditFeedback
                });
                ElementPlus.ElMessage.success('审核成功');
                this.fetchNotifications();
                this.fileAuditFeedback = ''; // 清空
                this.viewDetails(this.currentProject.id);
                this.fetchProjects();
            } catch(e) {
                const msg = (e && e.response && e.response.status === 404) ? '项目不存在或已被删除' : (e.response?.data?.error || '审核失败');
                ElementPlus.ElMessage.error(msg);
                if (this.currentProject && this.currentProject.id) {
                    const idx = this.projects.findIndex(p => p.id === this.currentProject.id);
                    if (idx >= 0) this.projects.splice(idx, 1);
                }
                this.fetchProjects();
                this.fetchCompetitions();
            }
        },
        
        downloadFile(file) {
            if (!file || !file.file_path) {
                ElementPlus.ElMessage.warning('文件路径不存在');
                return;
            }
            window.open(file.file_path, '_blank');
        },
        
        openCreateUserDialog() {
            this.showCreateUserDialog = true;
            this.createUserForm = { role: '', college: this.user?.college || '' };
        },
        async submitCreateUser() {
            if(!this.createUserForm.username || !this.createUserForm.role) {
                ElementPlus.ElMessage.warning('请填写必填项'); return;
            }
            this.submitting = true;
            try {
                await axios.post('/api/users', this.createUserForm);
                ElementPlus.ElMessage.success('用户创建成功');
                this.showCreateUserDialog = false;
                this.fetchUsers();
            } catch(e) { ElementPlus.ElMessage.error(e.response?.data?.error || '失败'); }
            finally { this.submitting = false; }
        },
        openEditUserDialog(user) {
            this.editUserForm = JSON.parse(JSON.stringify(user));
            this.editUserForm.password = ''; // clear password
            this.showEditUserDialog = true;
        },
        async submitEditUser() {
             if(!this.editUserForm.real_name || !this.editUserForm.role) {
                ElementPlus.ElMessage.warning('请填写必填项'); return;
            }
            this.submitting = true;
            try {
                await axios.put(`/api/users/${this.editUserForm.id}`, this.editUserForm);
                ElementPlus.ElMessage.success('用户更新成功');
                this.showEditUserDialog = false;
                this.fetchUsers();
            } catch(e) { ElementPlus.ElMessage.error(e.response?.data?.error || '失败'); }
            finally { this.submitting = false; }
        },
        async generateTempPassword(uid) {
            try {
                const res = await axios.post(`/api/users/${uid}/reset_password`);
                this.editUserForm.temp_password_display = res.data?.temp_password || '';
                if (this.editUserForm.temp_password_display) {
                    ElementPlus.ElMessage.success('已生成临时密码');
                } else {
                    ElementPlus.ElMessage.warning('未生成临时密码');
                }
            } catch(e) {
                ElementPlus.ElMessage.error(e.response?.data?.error || '生成失败');
            }
        },
        async deleteUser(user) {
            try {
                await ElementPlus.ElMessageBox.confirm(`确定要删除用户 ${user.username} (${user.real_name}) 吗?`, '警告', {
                    confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning'
                });
                await axios.delete(`/api/users/${user.id}`);
                ElementPlus.ElMessage.success('删除成功');
                this.fetchUsers();
            } catch(e) { 
                if(e !== 'cancel') ElementPlus.ElMessage.error(e.response?.data?.error || '删除失败'); 
            }
        },
        async deleteProject(row) {
            try {
                await ElementPlus.ElMessageBox.confirm(`确定要删除项目【${row.title}】(ID: ${row.id}) 吗?`, '警告', {
                    confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning'
                });
                await axios.delete(`/api/projects/${parseInt(row.id, 10)}`);
                ElementPlus.ElMessage.success('删除成功');
                this.fetchProjects();
            } catch(e) {
                if(e !== 'cancel') ElementPlus.ElMessage.error(e.response?.data?.error || '删除失败');
            }
        }
    }
};

// 3. Layout 组件
const Layout = {
    template: `
    <el-container class="app-wrapper">
        <el-header class="header">
            <div class="header-left">
                <div class="logo"><el-icon><Monitor /></el-icon> <span>项目管理系统</span></div>
            </div>
            <div class="header-right">
                <span class="user-info" v-if="user">
                    <el-avatar :size="32" icon="UserFilled"></el-avatar>
                    <span class="username">{{ user.real_name }} ({{ user.username }})</span>
                </span>
                <el-button type="danger" link @click="logout">退出</el-button>
            </div>
        </el-header>
        <el-main class="main-content">
            <router-view :user="user"></router-view>
        </el-main>
    </el-container>
    `,
    props: ['user'],
    methods: {
        async logout() {
            await axios.post('/api/logout');
            this.$emit('logout');
            this.$router.push('/login');
        }
    }
};

// --- 初始化 ---
const routes = [
    { path: '/login', component: Login },
    { path: '/', component: Layout, children: [{ path: '', component: Dashboard }] }
];
const router = createRouter({ history: createWebHashHistory(), routes });
const app = createApp({
    setup() {
        const user = ref(null);
        onMounted(async () => {
            try { const res = await axios.get('/api/me'); user.value = res.data; }
            catch(e) { if(router.currentRoute.value.path !== '/login') router.push('/login'); }
        });
        router.beforeEach(async (to, from, next) => {
            if (to.path !== '/login' && !user.value) {
                try { const res = await axios.get('/api/me'); user.value = res.data; next(); }
                catch(e) { next('/login'); }
            } else if (to.path === '/login' && user.value) { next('/'); } 
            else { next(); }
        });
        const handleLoginSuccess = (u) => { user.value = u; };
        const handleLogout = () => { user.value = null; };
        return { user, handleLoginSuccess, handleLogout };
    }
});

if (typeof ElementPlusIconsVue !== 'undefined') {
    for (const [key, component] of Object.entries(ElementPlusIconsVue)) { app.component(key, component); }
}
app.component('form-designer', FormDesigner);
app.use(router);
app.use(ElementPlus);
app.mount('#app');

// Hide loading mask
const loader = document.getElementById('app-loading');
if (loader) {
    loader.style.opacity = '0';
    setTimeout(() => loader.style.display = 'none', 500);
}
