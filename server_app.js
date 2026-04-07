const { createApp, ref, computed, onMounted } = Vue;
const { createRouter, createWebHashHistory } = VueRouter;

axios.interceptors.response.use(
    response => {
        if (response.data && typeof response.data === 'object' && 'code' in response.data && 'data' in response.data) {
            return { ...response, data: response.data.data };
        }
        return response;
    },
    error => {
        const res = error.response;
        if (res && res.data && res.data.message) {
            error.message = res.data.message;
        }
        return Promise.reject(error);
    }
);

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

const CNMU_GRADE_OPTIONS = ['大一', '大二', '大三', '大四', '研一', '研二', '研三', '博一', '博二', '博三'];

const STATUS_MAP = {
    'pending': { text: '待导师审核', type: 'warning' },
    'pending_teacher': { text: '待导师审核', type: 'warning' },
    'pending_college': { text: '待学院审核', type: 'warning' },
    'reviewing': { text: '学院盲评中', type: 'warning' },
    'college_recommended': { text: '学院评审完成', type: 'primary' },
    'approved': { text: '校级通过（公开）', type: 'success' },
    'pending_advisor_review': { text: '待指导教师初审', type: 'warning' },
    'college_review': { text: '待评审（学院赛）', type: 'warning' },
    'school_review': { text: '待评审（校赛）', type: 'warning' },
    'pending_college_recommendation': { text: '待学院确认推荐', type: 'warning' },
    'pending_school_recommendation': { text: '待学校确认推荐', type: 'warning' },
    'provincial_review': { text: '省赛评审', type: 'info' },
    'provincial': { text: '省赛', type: 'info' },
    'to_modify': { text: '待修改', type: 'danger' },
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

const CNMU_COLLEGE_MAJOR = {
    "文学与新闻传播学院": ["汉语言文学", "汉语国际教育", "新闻学", "广播电视学", "广告学"],
    "外语学院": ["英语", "日语", "翻译", "商务英语"],
    "音乐舞蹈学院": ["音乐学", "舞蹈表演"],
    "体育学院": ["社会体育指导与管理"],
    "美术学院": ["美术学", "绘画", "动画", "视觉传达设计", "环境设计", "服装与服饰设计", "建筑学"],
    "法学院": ["法学", "知识产权", "法学(数字法学卓越人才实验班)", "法学(涉外法治卓越人才实验班)"],
    "民族学与社会学学院": ["社会学", "社会工作", "民族学", "历史学", "文物与博物馆学"],
    "马克思主义学院": ["思想政治教育"],
    "中华民族共同体学院": [],
    "经济学院": ["经济学", "经济统计学", "金融学", "金融工程", "保险学", "国际经济与贸易", "数字经济"],
    "教育学院": ["教育学", "教育技术学", "应用心理学"],
    "管理学院": ["信息管理与信息系统", "工商管理", "市场营销", "会计学", "财务管理", "人力资源管理", "电子商务", "旅游管理"],
    "公共管理学院": ["政治学与行政学", "行政管理", "劳动与社会保障", "土地资源管理"],
    "国家安全学院": [],
    "化学与材料科学学院": ["应用化学", "材料化学", "高分子材料与工程", "化学工程与工艺"],
    "生命科学学院": ["生物技术", "食品质量与安全", "生物工程", "生物制药"],
    "资源与环境学院": ["水文与水资源工程", "资源循环科学与工程", "环境工程", "环境科学"],
    "药学院": ["化学生物学", "药学", "药物制剂", "药物分析"],
    "数学与统计学学院": ["数学与应用数学", "信息与计算科学", "应用统计学", "数据科学与大数据技术"],
    "电子信息工程学院（机器人学院）": ["电子信息工程", "通信工程", "光电信息科学与工程", "集成电路设计与集成系统"],
    "计算机学院（人工智能学院）": ["计算机科学与技术", "软件工程", "网络工程", "人工智能", "机械设计制造及其自动化", "自动化", "轨道交通信号与控制", "网络空间安全", "数据科学"],
    "生物医学工程学院": ["生物医学工程", "医学信息工程", "智能医学工程"],
    "预科教育学院": [],
    "创新创业学院": []
};

const CNMU_COLLEGES = Object.keys(CNMU_COLLEGE_MAJOR);

const CNMU_DEGREE_COLLEGE_PROGRAMS = {
    '本科': CNMU_COLLEGE_MAJOR,
    '硕士': {
        "文学与新闻传播学院": ["中国语言文学（一级学科硕士点）", "民俗学", "传播学"],
        "外语学院": ["外国语言文学（一级学科硕士点）"],
        "音乐舞蹈学院": ["中国少数民族艺术（音乐/舞蹈方向）"],
        "体育学院": ["体育（专业硕士）"],
        "美术学院": ["设计学（一级学科硕士点）", "美术与书法（专业硕士）", "设计（专业硕士）"],
        "法学院": ["法学（一级学科硕士点）", "法律（专业硕士）"],
        "民族学与社会学学院": ["民族学（一级学科硕士点）", "社会学（一级学科硕士点）", "中国史（一级学科硕士点）", "社会工作（专业硕士）", "文物与博物馆（专业硕士）"],
        "马克思主义学院": ["马克思主义理论（一级学科硕士点）"],
        "中华民族共同体学院": ["中华民族共同体学（交叉学科硕士点）", "中华民族学", "马克思主义民族理论与政策"],
        "经济学院": ["理论经济学（一级学科硕士点）", "应用经济学（一级学科硕士点）", "金融（专业硕士）", "应用统计（专业硕士）", "数字经济（专业硕士）"],
        "教育学院": ["教育学（一级学科硕士点）", "教育（专业硕士）"],
        "管理学院": ["工商管理学（一级学科硕士点）", "管理科学与工程（一级学科硕士点）", "会计（专业硕士）"],
        "公共管理学院": ["公共管理学（一级学科硕士点）"],
        "国家安全学院": ["国家安全学（一级学科硕士点）"],
        "化学与材料科学学院": ["化学（一级学科硕士点）", "材料与化工（专业硕士）"],
        "生命科学学院": ["生物学（一级学科硕士点）", "生物与医药（专业硕士）"],
        "资源与环境学院": ["环境科学与工程（一级学科硕士点）", "资源与环境（专业硕士）"],
        "药学院": ["药学（一级学科硕士点）", "中药学（一级学科硕士点）", "中药（专业硕士）"],
        "数学与统计学学院": ["数学（一级学科硕士点）"],
        "电子信息工程学院（机器人学院）": ["信息与通信工程（一级学科硕士点）", "光学工程（一级学科硕士点）", "电子信息（专业硕士）"],
        "计算机学院（人工智能学院）": ["计算机科学与技术（一级学科硕士点）", "电子信息（专业硕士-计算机技术方向）"],
        "生物医学工程学院": ["生物医学工程（一级学科硕士点）", "电子信息（专业硕士-生物医学工程方向）"]
    },
    '博士': {
        "文学与新闻传播学院": ["中国语言文学（博士点）"],
        "音乐舞蹈学院": ["中国少数民族艺术（博士点）"],
        "民族学与社会学学院": ["民族学（博士点）"],
        "中华民族共同体学院": ["中华民族共同体学（交叉学科博士点）", "中华民族学", "马克思主义民族理论与政策"],
        "经济学院": ["中国少数民族经济（博士点）"],
        "教育学院": ["教育学（博士点）"],
        "化学与材料科学学院": ["化学（博士点）"],
        "生命科学学院": ["生物学（博士点）"],
        "药学院": ["药学（博士点）"]
    }
};

const ORG_DEPARTMENTS = ["创新创业学院", "信息化建设管理处"];

const ROLE_FIELD2_OPTIONS = {
    system_admin: ["系统管理员"],
    school_approver: ["处长", "科长", "科员"],
    project_admin: ["科长", "科员", "项目专员"],
    college_approver: ["副院长", "教学秘书", "辅导员"],
    judge: ["教授", "副教授"],
    teacher: ["教授", "副教授", "讲师"]
};

// --- 组件定义 ---

// 1. 登录组件 (移除注册功能，由管理员创建账号)
const Login = {
    template: `
    <div class="login-container">
        <el-card class="login-card">
            <template #header>
                <div class="card-header">
                    <h2>大学生创新创业项目管理系统</h2>
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
                    <p style="color: #909399; font-size: 13px; margin-bottom: 10px;">—— 快速填充账号 ——</p>
                    <div style="display:flex; gap:8px; flex-wrap:wrap; justify-content: center;">
                        <el-tag size="small" type="info" style="cursor: pointer;" @click="fillQuick('teacher')">黄卓</el-tag>
                        <el-tag size="small" type="info" style="cursor: pointer;" @click="fillQuick('student')">学生</el-tag>
                        <el-tag size="small" type="info" style="cursor: pointer;" @click="fillQuick('judge')">评审</el-tag>
                        <el-tag size="small" type="info" style="cursor: pointer;" @click="fillQuick('college')">学院</el-tag>
                        <el-tag size="small" type="info" style="cursor: pointer;" @click="fillQuick('school')">学校</el-tag>
                        <el-tag size="small" type="success" style="cursor: pointer;" @click="fillQuick('proj_admin')">项目管理</el-tag>
                        <el-tag size="small" type="danger" style="cursor: pointer;" @click="fillQuick('admin')">管理员</el-tag>
                    </div>
                    <div style="margin-top: 6px; color:#909399; font-size: 12px;">默认密码：按账号预置</div>

                    <div style="margin-top: 14px; color:#c0c4cc; font-size: 12px;">—— 大挑评审测试账号 ——</div>
                    <div style="display:flex; gap:8px; flex-wrap:wrap; justify-content: center; margin-top: 10px;">
                        <el-tag size="small" type="warning" style="cursor: pointer;" @click="fillQuick('test_college_admin')">学院管理员</el-tag>
                        <el-tag size="small" type="warning" style="cursor: pointer;" @click="fillQuick('test_school_admin')">学校管理员</el-tag>
                        <el-tag size="small" type="info" style="cursor: pointer;" @click="fillQuick('test_college_judge1')">院赛评委1</el-tag>
                        <el-tag size="small" type="info" style="cursor: pointer;" @click="fillQuick('test_school_social_leader')">校赛社科组长</el-tag>
                        <el-tag size="small" type="info" style="cursor: pointer;" @click="fillQuick('test_school_science_leader')">校赛理工组长</el-tag>
                    </div>
                    <div style="margin-top: 8px; color:#909399; font-size: 12px;">测试账号默认密码：Test123456</div>
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
                    <el-form-item :label="identityLabel" required>
                        <el-input v-model="form.identity_number" @input="rememberIdentity(form.role, form.identity_number)"></el-input>
                    </el-form-item>
                    <el-form-item label="所属学院">
                        <el-select v-model="form.college" filterable style="width: 100%">
                            <el-option v-for="c in colleges" :key="c" :label="c" :value="c"></el-option>
                        </el-select>
                    </el-form-item>
                    <template v-if="form.role === 'student'">
                        <el-form-item label="专业">
                            <el-select v-model="form.department" filterable allow-create default-first-option style="width: 100%">
                                <el-option v-for="m in majorsForSelectedCollege" :key="m" :label="m" :value="m"></el-option>
                            </el-select>
                        </el-form-item>
                    </template>
                    <template v-else>
                        <el-form-item label="职称">
                            <el-select v-model="form.department" filterable allow-create default-first-option style="width: 100%">
                                <el-option v-for="t in teacherTitles" :key="t" :label="t" :value="t"></el-option>
                            </el-select>
                        </el-form-item>
                        <el-form-item label="教研室">
                            <el-input v-model="form.teaching_office"></el-input>
                        </el-form-item>
                    </template>
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
                identity_number: '',
                teaching_office: ''
            }
        }
    },
    computed: {
        colleges() {
            return CNMU_COLLEGES;
        },
        majorsForSelectedCollege() {
            const c = this.form.college;
            return Array.isArray(CNMU_COLLEGE_MAJOR[c]) ? CNMU_COLLEGE_MAJOR[c] : [];
        },
        teacherTitles() {
            return ROLE_FIELD2_OPTIONS.teacher || [];
        },
        identityLabel() {
            return this.form.role === 'student' ? '学号' : '工号';
        }
    },
    watch: {
        'form.role'(val) {
            const mem = this.loadIdentityMemory(val);
            if (!this.form.identity_number && mem) {
                this.form.identity_number = mem;
            }
            if (val === 'student') {
                this.form.teaching_office = '';
            }
        }
    },
    methods: {
        rememberIdentity(role, value) {
            try {
                const k = `id_mem_${role || 'unknown'}`;
                if (value === undefined || value === null) return;
                localStorage.setItem(k, String(value));
            } catch (e) {}
        },
        loadIdentityMemory(role) {
            try {
                const k = `id_mem_${role || 'unknown'}`;
                return localStorage.getItem(k) || '';
            } catch (e) { return ''; }
        },
        toggleMode() {
            this.isRegister = !this.isRegister;
            this.form = { username: '', password: '', role: 'student', real_name: '', college: '', department: '', identity_number: this.loadIdentityMemory('student'), teaching_office: '' };
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
                    this.$emit('login-success', res.data);
                    this.$router.push('/');
                }
            } catch (error) {
                ElementPlus.ElMessage.error(error.message || '操作失败');
            } finally {
                this.loading = false;
            }
        },
        fillQuick(type) {
            const map = {
                admin: { u: 'admin', p: 'admin123' },
                teacher: { u: '黄卓', p: 'hz123456' },
                student: { u: 'student1', p: 'student123' },
                judge: { u: 'judge1', p: 'admin123' },
                college: { u: 'col_approver', p: 'admin123' },
                school: { u: 'sch_approver', p: 'admin123' },
                proj_admin: { u: 'proj_admin', p: 'admin123' },
                test_college_admin: { u: 'test_college_admin_cs', p: 'Test123456' },
                test_school_admin: { u: 'test_school_admin', p: 'Test123456' },
                test_college_judge1: { u: 'test_cc_college_judge1', p: 'Test123456' },
                test_school_social_leader: { u: 'test_cc_school_social_leader', p: 'Test123456' },
                test_school_science_leader: { u: 'test_cc_school_science_leader', p: 'Test123456' }
            };
            const v = map[type];
            if (v) {
                this.form.username = v.u;
                this.form.password = v.p;
                ElementPlus.ElMessage.success('已自动填充：' + v.u);
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
    { 
        label: '团队成员', 
        key: 'members', 
        type: 'table', 
        required: true, 
        system: true, 
        placeholder: '请添加团队成员',
        columns: [
            { label: '姓名', key: 'name', width: 100 },
            { label: '学号', key: 'student_id', width: 120 },
            { label: '学院', key: 'college', width: 150 },
            { label: '专业', key: 'major', width: 150 },
            { label: '分工', key: 'role', width: 150 }
        ]
    },
    { 
        label: '经费预算', 
        key: 'extra_info.budget', 
        type: 'table', 
        required: true, 
        placeholder: '请填写经费预算',
        columns: [
            { label: '支出科目', key: 'item', width: 150 },
            { label: '预算金额(元)', key: 'amount', width: 120 },
            { label: '用途说明', key: 'usage', width: 250 }
        ]
    },
    { 
        label: '合作者信息（≤2人）', 
        key: 'extra_info.collaborators_individual', 
        type: 'table', 
        required: true, 
        placeholder: '个人项目合作者',
        columns: [
            { label: '姓名', key: '姓名', width: 90 },
            { label: '性别', key: '性别', width: 70 },
            { label: '年龄', key: '年龄', width: 70 },
            { label: '学历', key: '学历', width: 90 },
            { label: '所在单位', key: '所在单位', width: 160 }
        ]
    },
    { 
        label: '合作者信息（≤8-10人）', 
        key: 'extra_info.collaborators_team', 
        type: 'table', 
        required: true, 
        placeholder: '集体项目合作者',
        columns: [
            { label: '姓名', key: '姓名', width: 90 },
            { label: '性别', key: '性别', width: 70 },
            { label: '年龄', key: '年龄', width: 70 },
            { label: '学历', key: '学历', width: 90 },
            { label: '所在单位', key: '所在单位', width: 160 }
        ]
    },
    { label: '申报书附件', key: 'extra_info.attachments.application_doc', type: 'file', required: true, placeholder: '请上传申报书' },
    { label: '公司名称', key: 'extra_info.company_info.name', type: 'text', required: true, placeholder: '请输入公司名称' },
    { label: '统一社会信用代码', key: 'extra_info.company_info.code', type: 'text', required: false, placeholder: '请输入统一社会信用代码' },
    { label: '注册时间', key: 'extra_info.company_info.founded_date', type: 'date', required: false, placeholder: '请选择注册时间' },
    { label: '注册资本(万元)', key: 'extra_info.company_info.capital', type: 'number', required: false, placeholder: '请输入注册资本' },
    { label: '股权结构', key: 'extra_info.company_info.equity_structure', type: 'textarea', required: true, placeholder: '请描述股权结构' },
    { label: '所属行业', key: 'extra_info.industry', type: 'select', required: true, options: [], placeholder: '请选择所属行业' },
    { label: '入驻园区', key: 'extra_info.park', type: 'text', required: false, placeholder: '请输入入驻园区' },
    { label: '当前阶段', key: 'extra_info.stage', type: 'select', required: true, options: [{label:'创意',value:'idea'}, {label:'产品',value:'product'}, {label:'营收',value:'revenue'}, {label:'融资',value:'financing'}], placeholder: '请选择当前阶段' },
    { 
        label: '融资记录', 
        key: 'extra_info.company_info.investments', 
        type: 'table', 
        required: false, 
        placeholder: '请填写融资记录',
        columns: [
            { label: '融资时间', key: 'date', width: 120 },
            { label: '轮次', key: 'round', width: 100 },
            { label: '融资金额(万元)', key: 'amount', width: 120 },
            { label: '投资方', key: 'investor', width: 200 }
        ]
    },
    { label: '商业计划书', key: 'extra_info.attachments.business_plan', type: 'file', required: true, placeholder: '请上传商业计划书' },
    { label: '营业执照', key: 'extra_info.attachments.license', type: 'file', required: false, placeholder: '请上传营业执照' },
    { label: '参赛赛道', key: 'extra_info.track', type: 'select', required: true, options: [{label:'高教主赛道',value:'main'}, {label:'红旅赛道',value:'red'}, {label:'产业命题赛道',value:'industry'}], placeholder: '请选择参赛赛道' },
    { label: '参赛组别', key: 'extra_info.group', type: 'select', required: true, options: [{label:'本科生创意组',value:'undergrad_idea'}, {label:'研究生创意组',value:'grad_idea'}, {label:'创业组',value:'startup'}, {label:'公益组',value:'charity'}], placeholder: '请选择参赛组别' },
    { label: '行业痛点', key: 'extra_info.pain_points', type: 'textarea', required: true, placeholder: '请输入行业痛点' },
    { label: '商业模式', key: 'extra_info.business_model', type: 'richtext', required: true, placeholder: '请输入商业模式' },
    { label: '竞品分析', key: 'extra_info.competitor_analysis', type: 'richtext', required: false, placeholder: '请输入竞品分析' },
    { label: '路演PPT', key: 'extra_info.attachments.pitch_deck', type: 'file', required: true, placeholder: '请上传路演PPT' },
    { label: '1分钟视频', key: 'extra_info.attachments.video', type: 'file', required: false, placeholder: '请上传1分钟视频' },
    { 
        label: '获奖情况', 
        key: 'extra_info.awards', 
        type: 'table', 
        required: false, 
        placeholder: '请填写获奖情况',
        columns: [
            { label: '获奖时间', key: 'date', width: 120 },
            { label: '奖项名称', key: 'name', width: 200 },
            { label: '获奖等级', key: 'level', width: 120 },
            { label: '授奖单位', key: 'org', width: 150 }
        ]
    },
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
    { label: '产品演示', key: 'extra_info.attachments.product_demo', type: 'file', required: false, placeholder: '请上传产品演示' },
    { label: '借鉴往届项目', key: 'extra_info.borrowed_citations', type: 'select', required: false, options: [], placeholder: '请选择借鉴的往届项目' }
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
            if (!this.editingField.columns) this.editingField.columns = [];
            this.showFieldDialog = true;
        },
        // --- Table Column Management ---
        addColumn() {
            if (!this.editingField.columns) this.editingField.columns = [];
            this.editingField.columns.push({ label: '新列', key: 'col_' + Date.now(), width: 120 });
        },
        removeColumn(index) {
            this.editingField.columns.splice(index, 1);
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
                        <el-tag v-if="field.type === 'table'" size="small" type="success" style="margin-left: 5px;">{{ (field.columns?.length || 0) }} 列</el-tag>
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
                    
                    <el-tab-pane label="高级选项" v-if="['select', 'radio', 'checkbox', 'table'].includes(editingField.type)">
                        <div v-if="['select', 'radio', 'checkbox'].includes(editingField.type)">
                            <div v-for="(opt, idx) in editingField.options" :key="idx" style="display: flex; gap: 10px; margin-bottom: 10px;">
                                <el-input v-model="opt.label" placeholder="选项名"></el-input>
                                <el-input v-model="opt.value" placeholder="选项值"></el-input>
                                <el-button type="danger" circle icon="Delete" @click="removeOption(idx)"></el-button>
                            </div>
                            <el-button size="small" @click="addOption">+ 添加选项</el-button>
                        </div>
                        <div v-if="editingField.type === 'table'">
                            <el-alert title="配置表格列。如果是预设的“合作者信息”字段标识，系统将自动应用标准列。" type="info" :closable="false" style="margin-bottom: 15px;"></el-alert>
                            <div v-for="(col, idx) in editingField.columns" :key="idx" style="display: flex; gap: 10px; margin-bottom: 10px; align-items: center;">
                                <el-input v-model="col.label" placeholder="列名" style="width: 150px;"></el-input>
                                <el-input v-model="col.key" placeholder="标识" style="width: 120px;"></el-input>
                                <el-input-number v-model="col.width" placeholder="宽度" :min="50" :step="10" style="width: 120px;"></el-input-number>
                                <el-button type="danger" circle icon="Delete" @click="removeColumn(idx)"></el-button>
                            </div>
                            <el-button size="small" @click="addColumn">+ 添加表格列</el-button>
                        </div>
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
        <!-- Advisor Review Dialog -->
        <el-dialog v-model="showAdvisorReviewDialog" title="指导教师初审" width="600px">
            <el-form :model="advisorReviewForm" label-width="100px" v-if="currentAdvisorProject">
                <div style="margin-bottom: 20px; padding: 15px; background: #f8f9fa; border-radius: 4px;">
                    <p><strong>项目名称：</strong>{{ currentAdvisorProject.title }}</p>
                    <p><strong>作品类别：</strong>{{ currentAdvisorProject.project_type_label || '学术论文' }}</p>
                    <p><strong>申报学院：</strong>{{ currentAdvisorProject.college }}</p>
                </div>
                <el-form-item label="初审结果" required>
                    <el-radio-group v-model="advisorReviewForm.status">
                        <el-radio label="pass">通过 (进入院级评审)</el-radio>
                        <el-radio label="reject">驳回 (需要修改)</el-radio>
                    </el-radio-group>
                </el-form-item>
                <el-form-item label="审核意见" :required="advisorReviewForm.status === 'reject'">
                    <el-input type="textarea" v-model="advisorReviewForm.opinion" :rows="3" placeholder="请填写审核意见"></el-input>
                </el-form-item>
            </el-form>
            <template #footer>
                <el-button @click="showAdvisorReviewDialog = false">取消</el-button>
                <el-button type="primary" @click="submitAdvisorReview" :loading="submittingAdvisorReview">提交审核</el-button>
            </template>
        </el-dialog>

        <!-- Task Review Dialog (Enhanced Blind Review) -->
        <el-dialog v-model="showTaskReviewDialog" title="院级项目盲评" width="800px" top="5vh">
            <div v-if="currentTask" style="max-height: 75vh; overflow-y: auto; padding-right: 10px;">
                <el-alert title="盲评提示：系统已自动隐藏申报人及导师信息，请根据申报书内容进行客观公正评分。" type="info" show-icon :closable="false" class="mb-4"></el-alert>
                
                <div style="margin-bottom: 20px; padding: 15px; border: 1px solid #ebeef5; border-radius: 8px;">
                    <h3 style="margin-top: 0;">{{ currentTask.project_title }}</h3>
                    <div style="display: flex; gap: 20px; font-size: 14px; color: #666;">
                        <span>作品类别: {{ currentTask.project_type_label || '学术论文' }}</span>
                        <span>申报学院: {{ currentTask.project_college }}</span>
                    </div>
                </div>

                <el-form label-position="top">
                    <div v-for="item in currentTask.scoring_criteria" :key="item.key" style="margin-bottom: 25px; padding: 15px; background: #fafafa; border-radius: 8px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                            <span style="font-weight: bold; font-size: 16px;">{{ item.label }} (满分 {{ item.max }} 分)</span>
                            <el-input-number v-model="taskReviewForm.criteria_scores[item.key]" :min="0" :max="item.max" size="small"></el-input-number>
                        </div>
                        <div style="font-size: 13px; color: #999; margin-bottom: 10px;">{{ item.desc }}</div>
                        <el-input 
                            type="textarea" 
                            v-model="taskReviewForm.score_reasons[item.key]" 
                            placeholder="请填写打分理由" 
                            :rows="2"
                        ></el-input>
                    </div>

                    <el-divider>综合结论</el-divider>
                    
                    <el-form-item label="推荐结论" required>
                        <el-radio-group v-model="taskReviewForm.is_recommended">
                            <el-radio :label="true">推荐进入校赛</el-radio>
                            <el-radio :label="false">不推荐</el-radio>
                        </el-radio-group>
                    </el-form-item>

                    <el-form-item label="综合评审意见" required>
                        <el-input type="textarea" v-model="taskReviewForm.comments" :rows="4" placeholder="请填写详细的综合评审意见"></el-input>
                    </el-form-item>

                    <div style="margin: 20px 0; padding: 15px; background: #fff7e6; border: 1px solid #ffd591; border-radius: 4px;">
                        <el-checkbox v-model="taskReviewForm.declaration">
                            系统已自动检测利益关系，本人确认无其他未声明的利益冲突
                        </el-checkbox>
                    </div>
                </el-form>
            </div>
            <template #footer>
                <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
                    <div style="font-size: 18px; font-weight: bold; color: var(--primary-color);">
                        预计总分: {{ Object.values(taskReviewForm.criteria_scores).reduce((a, b) => (parseFloat(a) || 0) + (parseFloat(b) || 0), 0) }}
                    </div>
                    <div>
                        <el-button @click="showTaskReviewDialog = false">取消</el-button>
                        <el-button type="warning" @click="submitTaskReview('draft')" :loading="submitting">暂存</el-button>
                        <el-button type="primary" @click="submitTaskReview('completed')" :loading="submitting">确认提交</el-button>
                    </div>
                </div>
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

        <el-card v-if="['college_approver','school_approver','project_admin','system_admin'].includes(user?.role)" class="mb-4" shadow="hover">
            <template #header>
                <div class="card-header" style="display: flex; justify-content: space-between; align-items: center;">
                    <span><el-icon><Tools /></el-icon> 快速测试通道</span>
                    <div style="display:flex; gap: 10px;">
                        <el-button size="small" @click="showQuickTestDialog = true">查看测试账号</el-button>
                        <el-button size="small" type="primary" :loading="bootstrappingReviews" @click="bootstrapReviewsForProject1">一键初始化评审数据 (测试用)</el-button>
                    </div>
                </div>
            </template>
            <div style="color:#666; font-size: 12px; line-height: 20px;">
                推荐流程：先用管理员点击“一键初始化”，再用评委账号进入“我的评审任务”进行暂存/提交验证。
            </div>
        </el-card>

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
                <el-tab-pane label="指导教师初审" name="advisor_review" v-if="user?.role === 'teacher'">
                    <el-card shadow="hover">
                        <div style="display:flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                            <div style="color:#666; font-size: 12px;">
                                共 {{ advisorPendingProjects.length }} 条待审项目
                            </div>
                            <el-button size="small" @click="fetchAdvisorPendingProjects">刷新</el-button>
                        </div>
                        <el-table :data="advisorPendingProjects" border style="width: 100%">
                            <el-table-column prop="id" label="ID" width="60"></el-table-column>
                            <el-table-column prop="title" label="项目名称" min-width="200"></el-table-column>
                            <el-table-column prop="college" label="申报学院" width="150"></el-table-column>
                            <el-table-column label="状态" width="160">
                                <template #default="scope">
                                    <el-tag :type="getStatusTypeForRow(scope.row)">{{ getStatusTextForRow(scope.row) }}</el-tag>
                                </template>
                            </el-table-column>
                            <el-table-column label="操作" width="120" fixed="right">
                                <template #default="scope">
                                    <el-button size="small" type="primary" @click="openAdvisorReviewDialog(scope.row)">审核</el-button>
                                </template>
                            </el-table-column>
                        </el-table>
                    </el-card>
                </el-tab-pane>

                <el-tab-pane label="我的评审任务" name="my_reviews" v-if="['judge', 'teacher', 'college_approver', 'school_approver'].includes(user?.role)">
                    <el-card shadow="hover">
                        <div style="display:flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                            <div style="color:#666; font-size: 12px;">
                                共 {{ Array.isArray(myReviewTasks) ? myReviewTasks.length : 0 }} 条
                            </div>
                            <el-button size="small" @click="fetchMyReviewTasks" :loading="loadingReviews">刷新</el-button>
                        </div>
                        <el-table :data="myReviewTasks" border style="width: 100%" v-loading="loadingReviews">
                            <el-table-column prop="id" label="任务ID" width="80"></el-table-column>
                            <el-table-column prop="project_title" label="项目名称" min-width="200"></el-table-column>
                            <el-table-column label="赛事类型" width="120">
                                <template #default="scope">
                                    {{ getProjectTypeLabel(scope.row.project_type) }}
                                </template>
                            </el-table-column>
                            <el-table-column label="评审级别" width="100">
                                <template #default="scope">
                                    {{ scope.row.review_level === 'school' ? '校赛' : '学院赛' }}
                                </template>
                            </el-table-column>
                            <el-table-column label="状态" width="100">
                                <template #default="scope">
                                    <el-tag :type="scope.row.status === 'completed' ? 'success' : (scope.row.status === 'draft' ? 'warning' : 'info')">
                                        {{ scope.row.status === 'completed' ? '已提交' : (scope.row.status === 'draft' ? '暂存' : '待评审') }}
                                    </el-tag>
                                </template>
                            </el-table-column>
                            <el-table-column prop="score" label="总分" width="80"></el-table-column>
                            <el-table-column label="操作" width="120" fixed="right">
                                <template #default="scope">
                                    <el-button size="small" type="primary" @click="openTaskReviewDialog(scope.row)">
                                        {{ scope.row.status === 'completed' ? '查看' : '评审' }}
                                    </el-button>
                                </template>
                            </el-table-column>
                        </el-table>
                    </el-card>
                </el-tab-pane>
                <el-tab-pane label="评审管理(管理员)" name="review_management" v-if="['college_approver', 'school_approver', 'project_admin'].includes(user?.role)">
                    <el-card shadow="hover">
                        <div style="margin-bottom: 20px;">
                            <el-button type="primary" @click="calcReviewRank" :loading="calculatingRank">计算平均分与排名</el-button>
                            <span style="color: #666; margin-left: 10px; font-size: 12px;">注：会自动计算当前评审级别下所有已提交打分的平均分并生成排名</span>
                        </div>
                        <el-table :data="filteredProjects" border style="width: 100%" v-loading="loading">
                            <el-table-column prop="id" label="ID" width="60"></el-table-column>
                            <el-table-column prop="title" label="项目名称" min-width="150"></el-table-column>
                            <el-table-column label="当前级别" width="100">
                                <template #default="scope">{{ scope.row.current_level === 'school' ? '校赛' : '学院赛' }}</template>
                            </el-table-column>
                            <el-table-column prop="college_avg_score" label="院赛均分" width="100"></el-table-column>
                            <el-table-column prop="college_rank" label="院赛排名" width="100"></el-table-column>
                            <el-table-column prop="school_avg_score" label="校赛均分" width="100" v-if="user?.role === 'school_approver' || user?.role === 'project_admin'"></el-table-column>
                            <el-table-column prop="school_rank" label="校赛排名" width="100" v-if="user?.role === 'school_approver' || user?.role === 'project_admin'"></el-table-column>
                            <el-table-column label="操作" width="200" fixed="right">
                                <template #default="scope">
                                    <el-button size="small" type="warning" @click="openAssignDialog(scope.row)">分配评委</el-button>
                                    <el-button size="small" type="success" v-if="scope.row.current_level === 'college' && user?.role === 'college_approver'" @click="recommendProject(scope.row, 'school')">推荐至校赛</el-button>
                                </template>
                            </el-table-column>
                        </el-table>
                    </el-card>
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
                    
                    <el-table :data="filteredProjects" style="width: 100%" v-loading="loading">
                        <el-table-column prop="id" label="ID" width="50"></el-table-column>
                        <el-table-column prop="title" label="项目名称"></el-table-column>
                        <el-table-column label="类型" width="120">
                            <template #default="scope">
                                {{ getProjectTypeLabel(scope.row.project_type) }}
                            </template>
                        </el-table-column>
                        <el-table-column label="级别" width="100">
                            <template #default="scope">
                                {{ getLevelLabel(scope.row.level) }}
                            </template>
                        </el-table-column>
                        <el-table-column prop="leader_name" label="负责人" width="100"></el-table-column>
                        <el-table-column label="核心材料" width="140">
                            <template #default="scope">
                                <template v-if="scope.row.extra_info && scope.row.extra_info.attachments">
                                    <!-- 优先展示最有代表性的核心材料 -->
                                    <template v-if="scope.row.extra_info.attachments.business_plan">
                                        <el-link :href="scope.row.extra_info.attachments.business_plan" target="_blank" type="primary">查看商业计划书</el-link>
                                    </template>
                                    <template v-else-if="scope.row.extra_info.attachments.ns_full_text">
                                        <el-link :href="scope.row.extra_info.attachments.ns_full_text" target="_blank" type="primary">查看论文/报告</el-link>
                                    </template>
                                    <template v-else-if="scope.row.extra_info.attachments.full_paper">
                                        <el-link :href="scope.row.extra_info.attachments.full_paper" target="_blank" type="primary">查看论文/报告</el-link>
                                    </template>
                                    <template v-else-if="scope.row.extra_info.attachments.application_doc">
                                        <el-link :href="scope.row.extra_info.attachments.application_doc" target="_blank" type="primary">查看申报书</el-link>
                                    </template>
                                    <template v-else-if="scope.row.extra_info.attachments.report">
                                        <el-link :href="scope.row.extra_info.attachments.report" target="_blank" type="primary">查看报告</el-link>
                                    </template>
                                    <template v-else-if="scope.row.extra_info.attachments.proof_data">
                                        <el-link :href="scope.row.extra_info.attachments.proof_data" target="_blank" type="primary">查看运营证明</el-link>
                                    </template>
                                    <template v-else-if="scope.row.extra_info.attachments.pitch_deck">
                                        <el-link :href="scope.row.extra_info.attachments.pitch_deck" target="_blank" type="primary">查看路演PPT</el-link>
                                    </template>
                                    <span v-else style="color:#999">未上传</span>
                                </template>
                                <span v-else style="color:#999">未上传</span>
                            </template>
                        </el-table-column>
                        <el-table-column label="状态" width="160">
                            <template #default="scope">
                                <el-tag :type="getStatusTypeForRow(scope.row)">{{ getStatusTextForRow(scope.row) }}</el-tag>
                            </template>
                        </el-table-column>
                        <el-table-column label="操作" width="250" fixed="right">
                            <template #default="scope">
                                <el-button size="small" @click="viewDetails(scope.row.id)">详情</el-button>
                                
                                <!-- 导师审批 -->
                                <template v-if="user?.role === 'teacher' && canUserAudit(scope.row) && isTemplateNeedingTeacherAudit(scope.row)">
                                    <el-button size="small" type="success" @click="openAuditDialog(scope.row, 'approve')">通过</el-button>
                                    <el-button size="small" type="danger" @click="openAuditDialog(scope.row, 'reject')">驳回</el-button>
                                </template>

                                <!-- 学院审批 -->
                                <template v-if="user?.role === 'college_approver' && canUserAudit(scope.row)">
                                    <el-button size="small" type="success" @click="openAuditDialog(scope.row, 'approve')">学院通过</el-button>
                                    <el-button size="small" type="danger" @click="openAuditDialog(scope.row, 'reject')">学院驳回</el-button>
                                </template>

                                <!-- 学校审批 -->
                                <template v-if="user?.role === 'school_approver' && canUserAudit(scope.row)">
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
                                <template v-if="user?.role === 'student' && (scope.row.status === 'rejected' || scope.row.status === 'pending' || scope.row.status === 'pending_advisor_review' || scope.row.status === 'to_modify' || scope.row.status === 'advisor_approved' || scope.row.status === 'college_approved')">
                                     <el-button size="small" type="warning" :disabled="!scope.row || !scope.row.id" @click="editProject(scope.row)">
                                         {{ (scope.row.status === 'rejected' || scope.row.status === 'to_modify') ? '修改重报' : '修改' }}
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
                                 <el-tag v-if="scope.row.system_type" size="small" type="success" style="margin-left: 5px">{{ scope.row.system_type }}</el-tag>
                                 <el-tag v-if="scope.row.competition_level" size="small" type="warning" style="margin-left: 5px">{{ scope.row.competition_level }}</el-tag>
                             </template>
                         </el-table-column>
                         <el-table-column prop="school_organizer" label="承办单位" width="150"></el-table-column>
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
                                        :disabled="!scope.row.project_id || Number(scope.row.project_id) <= 0"
                                        @click="editProject({id: scope.row.project_id})">
                                        修改报名
                                    </el-button>
                                    <el-button 
                                        v-else 
                                        type="info" 
                                        size="small"
                                        :disabled="!scope.row.project_id || Number(scope.row.project_id) <= 0"
                                        @click="viewDetails(scope.row.project_id)">
                                        查看项目
                                    </el-button>
                                </template>
                                <el-button v-else-if="scope.row.status === 'active'" type="primary" size="small" @click="applyCompetition(scope.row)">
                                    报名参赛
                                </el-button>
                                <el-button v-else size="small" disabled>不可报名</el-button>
                            </template>
                        </el-table-column>
                     </el-table>
                </el-tab-pane>

                <!-- 赛事管理 (项目管理员可见) -->
                <el-tab-pane v-if="canManageCompetitions" label="申报批次管理" name="comp_mgmt">
                     <div class="filter-bar">
                         <el-button type="primary" @click="openCompDialog()">发布申报批次</el-button>
                     </div>
                     <el-table :data="competitions" style="width: 100%" v-loading="loading">
                        <el-table-column prop="id" label="ID" width="60"></el-table-column>
                        <el-table-column prop="title" label="批次名称" min-width="200">
                             <template #default="scope">
                                 <span>{{ scope.row.title }}</span>
                                 <el-tag v-if="scope.row.system_type" size="small" type="success" style="margin-left: 5px">{{ scope.row.system_type }}</el-tag>
                             </template>
                        </el-table-column>
                        <el-table-column prop="competition_level" label="赛事等级" width="100"></el-table-column>
                        <el-table-column prop="status" label="状态" width="100">
                            <template #default="scope">
                                <el-tag :type="scope.row.status === 'active' ? 'success' : (scope.row.status === 'upcoming' ? 'info' : 'info')">
                                    {{ scope.row.status === 'active' ? '进行中' : (scope.row.status === 'upcoming' ? '未开始' : '已结束') }}
                                </el-tag>
                            </template>
                        </el-table-column>
                        <el-table-column prop="school_organizer" label="承办单位"></el-table-column>
                        <el-table-column label="操作" width="150">
                            <template #default="scope">
                                <el-button size="small" @click="openCompDialog(scope.row)">编辑</el-button>
                                <el-button size="small" type="danger" @click="deleteCompetition(scope.row.id)">删除</el-button>
                            </template>
                        </el-table-column>
                    </el-table>
               </el-tab-pane>

                <el-tab-pane v-if="canManageAwards" label="获奖记录管理" name="award_mgmt">
                    <div class="filter-bar" style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;">
                        <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;">
                            <el-button type="primary" @click="openAwardDialog()">新增获奖记录</el-button>
                            <el-button @click="fetchAwards">刷新</el-button>
                        </div>
                    </div>
                    <el-table :data="awardsRecords" style="width: 100%" v-loading="awardsRecordsLoading">
                        <el-table-column prop="id" label="ID" width="70"></el-table-column>
                        <el-table-column prop="project_title" label="项目名称" min-width="220"></el-table-column>
                        <el-table-column prop="stage" label="阶段" width="90">
                            <template #default="scope">{{ getReviewStageText(scope.row.stage) }}</template>
                        </el-table-column>
                        <el-table-column prop="award_level" label="获奖等级" width="120">
                            <template #default="scope">{{ getAwardLevelText(scope.row.award_level) }}</template>
                        </el-table-column>
                        <el-table-column prop="award_name" label="奖项名称" min-width="160"></el-table-column>
                        <el-table-column prop="award_time" label="获奖时间" width="120"></el-table-column>
                        <el-table-column prop="issuer" label="颁奖单位" min-width="160"></el-table-column>
                        <el-table-column prop="created_at" label="录入时间" width="170"></el-table-column>
                        <el-table-column label="操作" width="160" fixed="right">
                            <template #default="scope">
                                <el-button size="small" @click="openAwardDialog(scope.row)">编辑</el-button>
                                <el-button size="small" type="danger" @click="deleteAward(scope.row.id)">删除</el-button>
                            </template>
                        </el-table-column>
                    </el-table>
                </el-tab-pane>

                <el-tab-pane v-if="canManageJiebangTopics" label="揭榜挂帅选题管理" name="jiebang_topics">
                    <div class="filter-bar" style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;">
                        <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;">
                            <el-button type="primary" @click="openJiebangTopicDialog()">新增选题</el-button>
                            <el-button @click="fetchJiebangAdminList">刷新</el-button>
                        </div>
                        <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;">
                            <el-input v-model="jiebangAdmin.groupNo" placeholder="项目群编号" style="width:120px;" clearable></el-input>
                            <el-select v-model="jiebangAdmin.enabled" placeholder="启用状态" style="width:120px;" clearable>
                                <el-option label="启用" :value="1"></el-option>
                                <el-option label="禁用" :value="0"></el-option>
                            </el-select>
                            <el-input v-model="jiebangAdmin.keyword" placeholder="关键词" style="width:220px;" clearable></el-input>
                        </div>
                    </div>

                    <el-table :data="jiebangAdmin.list" style="width:100%;" v-loading="jiebangAdmin.loading">
                        <el-table-column prop="id" label="ID" width="80"></el-table-column>
                        <el-table-column prop="group_no" label="群" width="60"></el-table-column>
                        <el-table-column prop="group_name" label="项目群" min-width="220"></el-table-column>
                        <el-table-column prop="topic_no" label="序号" width="70"></el-table-column>
                        <el-table-column prop="topic_title" label="选题标题" min-width="240"></el-table-column>
                        <el-table-column prop="enabled" label="启用" width="80">
                            <template #default="scope">
                                <el-tag :type="Number(scope.row.enabled) ? 'success' : 'info'">{{ Number(scope.row.enabled) ? '启用' : '禁用' }}</el-tag>
                            </template>
                        </el-table-column>
                        <el-table-column prop="updated_at" label="更新时间" width="170"></el-table-column>
                        <el-table-column label="操作" width="160" fixed="right">
                            <template #default="scope">
                                <el-button size="small" @click="openJiebangTopicDialog(scope.row)">编辑</el-button>
                                <el-button size="small" type="danger" @click="deleteJiebangTopic(scope.row)">删除</el-button>
                            </template>
                        </el-table-column>
                    </el-table>

                    <el-dialog v-model="jiebangAdmin.showDialog" :title="jiebangAdmin.isEdit ? '编辑选题' : '新增选题'" width="720px">
                        <el-form :model="jiebangAdmin.form" label-width="100px">
                            <el-row :gutter="20">
                                <el-col :span="8">
                                    <el-form-item label="年份" required>
                                        <el-input v-model="jiebangAdmin.form.year" disabled></el-input>
                                    </el-form-item>
                                </el-col>
                                <el-col :span="8">
                                    <el-form-item label="项目群编号" required>
                                        <el-input-number v-model="jiebangAdmin.form.group_no" :min="1" :max="99" style="width:100%;"></el-input-number>
                                    </el-form-item>
                                </el-col>
                                <el-col :span="8">
                                    <el-form-item label="序号" required>
                                        <el-input-number v-model="jiebangAdmin.form.topic_no" :min="1" :max="999" style="width:100%;"></el-input-number>
                                    </el-form-item>
                                </el-col>
                            </el-row>
                            <el-form-item label="项目群名称" required>
                                <el-input v-model="jiebangAdmin.form.group_name" placeholder="例如：人工智能+应用项目群"></el-input>
                            </el-form-item>
                            <el-form-item label="选题标题" required>
                                <el-input v-model="jiebangAdmin.form.topic_title"></el-input>
                            </el-form-item>
                            <el-form-item label="选题描述">
                                <el-input type="textarea" :rows="4" v-model="jiebangAdmin.form.topic_desc"></el-input>
                            </el-form-item>
                            <el-form-item label="启用">
                                <el-switch v-model="jiebangAdmin.form.enabled" :active-value="1" :inactive-value="0"></el-switch>
                            </el-form-item>
                        </el-form>
                        <template #footer>
                            <el-button @click="jiebangAdmin.showDialog = false">取消</el-button>
                            <el-button type="primary" :loading="jiebangAdmin.loading" @click="saveJiebangTopic">保存</el-button>
                        </template>
                    </el-dialog>
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
                <el-card shadow="never" class="mt-4" header="权限模式配置">
                    <el-form label-width="110px">
                        <el-form-item label="权限模式">
                            <el-select v-model="permissionModeDraft" style="width: 260px" @change="confirmPermissionModeChange">
                                <el-option label="混合模式（默认）" value="mixed"></el-option>
                                <el-option label="严格模式" value="strict"></el-option>
                            </el-select>
                            <span style="margin-left: 10px; color: #999; font-size: 12px;">
                                当前生效：{{ permissionMode === 'strict' ? '严格模式' : '混合模式' }}
                            </span>
                        </el-form-item>
                        <el-form-item>
                            <el-alert
                                v-if="permissionModeDraft === 'strict'"
                                title="严格模式：学校管理员/学院管理员将失去用户管理权限（增删改查/审核等），仅系统管理员保留。"
                                type="warning"
                                :closable="false"
                                show-icon>
                            </el-alert>
                            <el-alert
                                v-else
                                title="混合模式：系统管理员全权限；学校管理员可管理全校用户；学院管理员可管理本院用户。"
                                type="info"
                                :closable="false"
                                show-icon>
                            </el-alert>
                        </el-form-item>
                    </el-form>
                </el-card>
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
        <el-dialog v-model="showCreateDialog" :title="createDialogTitle" width="900px" destroy-on-close top="5vh" @close="handleDialogClose">
            <el-steps v-if="maxCreateStep === 2" :active="activeStep" finish-status="success" align-center style="margin-bottom: 20px">
                <el-step title="基本信息"></el-step>
                <el-step title="详细信息"></el-step>
                <el-step title="团队成员"></el-step>
            </el-steps>
            <el-steps v-else :active="0" finish-status="success" align-center style="margin-bottom: 20px">
                <el-step title="报名信息"></el-step>
            </el-steps>

            <el-form :model="createForm" label-width="110px" ref="createFormRef" size="default">
                <!-- Dynamic Form Rendering (Step 1) -->
                <div v-show="activeStep === 0">
                    <el-row :gutter="20">
                        <el-col :span="showJiebangTopicPanel ? 16 : 24">
                    <template v-if="createForm.form_config?.groups && createForm.form_config.groups.length > 0">
                        <template v-for="(group, gIndex) in createForm.form_config.groups" :key="gIndex">
                        <div v-if="shouldShow(createForm, group)">
                            <el-divider v-if="group.title" content-position="left">{{ group.title }}</el-divider>
                            <template v-if="isAdvisorGroup(group)">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                                    <span style="color: #666;">默认至少1名，最多3名</span>
                                    <el-button size="small" type="primary" @click="addAdvisor" :disabled="createForm.extra_info.advisors.length >= 3">添加指导教师</el-button>
                                </div>
                                <el-card v-for="(a, idx) in createForm.extra_info.advisors" :key="idx" shadow="never" style="margin-bottom: 12px;">
                                    <template #header>
                                        <div style="display: flex; justify-content: space-between; align-items: center;">
                                            <span>指导教师{{ idx + 1 }}（{{ getAdvisorRankLabel(idx) }}）</span>
                                            <el-button v-if="createForm.extra_info.advisors.length > 1 && idx > 0" type="danger" link size="small" @click="removeAdvisor(idx)">删除</el-button>
                                        </div>
                                    </template>
                                    <el-form-item label="主次标识" required>
                                        <el-radio-group :model-value="idx" disabled>
                                            <el-radio :label="0">第一指导教师</el-radio>
                                            <el-radio :label="1">第二指导教师</el-radio>
                                            <el-radio :label="2">第三指导教师</el-radio>
                                        </el-radio-group>
                                    </el-form-item>
                                    <el-row :gutter="20">
                                        <el-col :span="12">
                                            <el-form-item label="姓名" required>
                                                <el-input v-model="a.name" placeholder="请输入姓名"></el-input>
                                            </el-form-item>
                                        </el-col>
                                        <el-col :span="12">
                                            <el-form-item label="职称" required>
                                                <el-select v-model="a.title" style="width: 100%" placeholder="请选择职称" filterable>
                                                    <el-option v-for="opt in advisorTitleOptions" :key="opt" :label="opt" :value="opt"></el-option>
                                                </el-select>
                                            </el-form-item>
                                        </el-col>
                                    </el-row>
                                    <el-row :gutter="20">
                                        <el-col :span="12">
                                            <el-form-item label="所在单位" required>
                                                <el-select v-model="a.org" style="width: 100%" placeholder="所在学院/单位" filterable allow-create default-first-option>
                                                    <el-option v-for="opt in advisorOrgOptions" :key="opt" :label="opt" :value="opt"></el-option>
                                                </el-select>
                                            </el-form-item>
                                        </el-col>
                                        <el-col :span="12">
                                            <el-form-item v-if="shouldShowAdvisorGuidanceType" label="指导类型" required>
                                                <el-select v-model="a.guidance_type" style="width: 100%">
                                                    <el-option label="校内导师" value="校内导师"></el-option>
                                                    <el-option label="企业导师" value="企业导师"></el-option>
                                                </el-select>
                                            </el-form-item>
                                            <el-form-item v-else label="指导类型">
                                                <el-input :model-value="'校内导师'" disabled></el-input>
                                            </el-form-item>
                                        </el-col>
                                    </el-row>
                                    <el-row :gutter="20">
                                        <el-col :span="12">
                                            <el-form-item label="研究领域" required>
                                                <el-input v-model="a.research_area" placeholder="请输入研究领域"></el-input>
                                            </el-form-item>
                                        </el-col>
                                        <el-col :span="12">
                                            <el-form-item label="联系电话" required>
                                                <el-input v-model="a.phone" placeholder="请输入联系电话"></el-input>
                                            </el-form-item>
                                        </el-col>
                                    </el-row>
                                </el-card>
                            </template>
                            <template v-else>
                                <el-row :gutter="20">
                                    <template v-for="(field, fIndex) in group.fields" :key="fIndex">
                                    <el-col v-if="shouldShow(createForm, field)" :span="field.type === 'textarea' || field.type === 'richtext' || field.type === 'table' ? 24 : 12">
                                        <el-form-item :label="field.label" :required="field.required">
                                            <el-input
                                                v-if="field.type === 'text'"
                                                :model-value="getFieldValue(createForm, field.key)"
                                                @update:modelValue="val => setFieldValue(createForm, field.key, val)"
                                                :placeholder="field.placeholder"
                                                :disabled="field.disabled"></el-input>
                                            
                                            <el-input
                                                v-if="field.type === 'textarea'"
                                                type="textarea"
                                                :rows="3"
                                                :model-value="getFieldValue(createForm, field.key)"
                                                @update:modelValue="val => setFieldValue(createForm, field.key, val)"
                                                :placeholder="field.placeholder"
                                                :disabled="field.disabled"></el-input>

                                            <el-input
                                                v-if="field.type === 'richtext'"
                                                type="textarea"
                                                :rows="6"
                                                :model-value="getFieldValue(createForm, field.key)"
                                                @update:modelValue="val => setFieldValue(createForm, field.key, val)"
                                                :placeholder="field.placeholder"
                                                :disabled="field.disabled"></el-input>
                                            
                                            <el-select
                                                v-if="field.type === 'select'"
                                                :model-value="getFieldValue(createForm, field.key)"
                                                @update:modelValue="val => setFieldValue(createForm, field.key, val)"
                                                style="width: 100%"
                                                :placeholder="field.placeholder"
                                                :disabled="field.disabled"
                                                :filterable="true">
                                                <template v-if="field.key === 'project_type'">
                                                    <el-option v-for="t in allowedProjectTypes" :key="t.value" :label="t.label" :value="t.value"></el-option>
                                                </template>
                                                <template v-else-if="field.key === 'college'">
                                                    <el-option v-for="c in colleges" :key="c" :label="c" :value="c"></el-option>
                                                </template>
                                                <template v-else-if="field.key === 'department' || String(field.key).endsWith('.department')">
                                                    <el-option v-for="m in getMajorsByCollege(getFieldValue(createForm, 'extra_info.leader_info.college') || getFieldValue(createForm, 'college'))" :key="m" :label="m" :value="m"></el-option>
                                                </template>
                                                <template v-else-if="field.key === 'inspiration_source'">
                                                     <el-option v-for="item in inspirationOptions" :key="item.value" :label="item.label" :value="item.value">
                                                        <span style="float: left">{{ item.label }}</span>
                                                        <span style="float: right; color: #8492a6; font-size: 13px">{{ item.summary ? item.summary.substring(0, 20) + '...' : '' }}</span>
                                                     </el-option>
                                                </template>
                                                <template v-else>
                                                    <el-option v-for="opt in field.options" :key="opt.value" :label="opt.label" :value="opt.value"></el-option>
                                                </template>
                                            </el-select>
                                            
                                            <el-date-picker
                                                v-if="field.type === 'date'"
                                                :model-value="getFieldValue(createForm, field.key)"
                                                @update:modelValue="val => setFieldValue(createForm, field.key, val)"
                                                type="date"
                                                value-format="YYYY-MM-DD"
                                                style="width: 100%"
                                                :placeholder="field.placeholder"></el-date-picker>
                                            
                                            <el-input-number
                                                v-if="field.type === 'number'"
                                                :model-value="getFieldValue(createForm, field.key)"
                                                @update:modelValue="val => setFieldValue(createForm, field.key, val)"
                                                style="width: 100%"
                                                :min="0"></el-input-number>
                                            
                                            <el-radio-group
                                                v-if="field.type === 'radio'"
                                                :model-value="getFieldValue(createForm, field.key)"
                                                @update:modelValue="val => setFieldValue(createForm, field.key, val)">
                                                <el-radio v-for="opt in field.options" :key="opt.value" :label="opt.value">{{ opt.label }}</el-radio>
                                            </el-radio-group>

                                            <el-checkbox-group
                                                v-if="field.type === 'checkbox'"
                                                :model-value="Array.isArray(getFieldValue(createForm, field.key)) ? getFieldValue(createForm, field.key) : []"
                                                @update:modelValue="val => setFieldValue(createForm, field.key, val)">
                                                <el-checkbox v-for="opt in field.options" :key="opt.value" :label="opt.value">{{ opt.label }}</el-checkbox>
                                            </el-checkbox-group>

                                            <div v-if="field.type === 'file'">
                                                <input type="file" :accept="field.accept" @change="(e) => handleFileUpload(e, field.key)">
                                                <div v-if="getFieldValue(createForm, field.key)" style="margin-top: 5px;">
                                                    <el-tag type="success" style="margin-right: 10px;">已上传</el-tag>
                                                    <el-link :href="getFieldValue(createForm, field.key)" target="_blank" type="primary" style="margin-right: 10px;">查看</el-link>
                                                    <el-button type="danger" link size="small" @click="setFieldValue(createForm, field.key, '')">删除</el-button>
                                                </div>
                                                <div v-if="field.placeholder" style="font-size: 12px; color: #999;">{{ field.placeholder }}</div>
                                            </div>

                                            <div v-if="field.type === 'table' && getEffectiveTableColumns(field).length > 0">
                                                <div v-if="isCollaboratorsTableField(field)" style="font-size: 12px; color: #999; margin-bottom: 6px;">
                                                    {{ getCollaboratorsLimitHint(createForm, field.key) }}
                                                </div>
                                                <div style="margin-bottom: 6px;">
                                                    <el-button size="small" type="primary" @click="addTableRowSmart(createForm, field)">新增</el-button>
                                                </div>
                                                <div v-if="isCollaboratorsTableField(field)" style="width: 100%; overflow-x: auto; max-width: 100%;">
                                                    <el-table
                                                        :data="getTableRows(createForm, field.key)"
                                                        border
                                                        size="small"
                                                        style="width: 100%;">
                                                        <el-table-column
                                                            v-for="col in getEffectiveTableColumns(field)"
                                                            :key="col.key"
                                                            :prop="col.key"
                                                            :label="col.label"
                                                            :min-width="col.width || 120">
                                                            <template #default="scope">
                                                                <el-select
                                                                    v-if="isCollaboratorsTableField(field) && col.key === '学历'"
                                                                    :model-value="scope.row[col.key]"
                                                                    @update:modelValue="val => updateCollaboratorTableCell(createForm, field.key, scope.$index, col.key, val)"
                                                                    style="width: 100%">
                                                                    <el-option label="本科" value="本科"></el-option>
                                                                    <el-option label="硕士" value="硕士"></el-option>
                                                                    <el-option label="博士" value="博士"></el-option>
                                                                </el-select>
                                                                <el-select
                                                                    v-else-if="isCollaboratorsTableField(field) && col.key === '学院'"
                                                                    :model-value="scope.row[col.key]"
                                                                    @update:modelValue="val => updateCollaboratorTableCell(createForm, field.key, scope.$index, col.key, val)"
                                                                    filterable
                                                                    style="width: 100%">
                                                                    <el-option v-for="c in getCollaboratorCollegeOptions(scope.row['学历'])" :key="c" :label="c" :value="c"></el-option>
                                                                </el-select>
                                                                <el-select
                                                                    v-else-if="isCollaboratorsTableField(field) && col.key === '专业'"
                                                                    :model-value="scope.row[col.key]"
                                                                    @update:modelValue="val => updateCollaboratorTableCell(createForm, field.key, scope.$index, col.key, val)"
                                                                    filterable
                                                                    style="width: 100%">
                                                                    <el-option v-for="m in getCollaboratorMajorOptions(scope.row)" :key="m" :label="m" :value="m"></el-option>
                                                                </el-select>
                                                                <el-input
                                                                    v-else-if="isCollaboratorsTableField(field) && col.key === '承担工作'"
                                                                    type="textarea"
                                                                    :rows="2"
                                                                    :model-value="scope.row[col.key]"
                                                                    @update:modelValue="val => updateTableCell(createForm, field.key, scope.$index, col.key, val)"
                                                                ></el-input>
                                                                <el-input
                                                                    v-else
                                                                    :model-value="scope.row[col.key]"
                                                                    @update:modelValue="val => updateTableCell(createForm, field.key, scope.$index, col.key, val)"
                                                                ></el-input>
                                                            </template>
                                                        </el-table-column>
                                                        <el-table-column label="操作" width="80" fixed="right">
                                                            <template #default="scope">
                                                                <el-button type="danger" link size="small" @click="removeTableRow(createForm, field.key, scope.$index)">删除</el-button>
                                                            </template>
                                                        </el-table-column>
                                                    </el-table>
                                                </div>
                                                <div v-else style="width: 100%;">
                                                    <el-table :data="getTableRows(createForm, field.key)" border size="small" style="width: 100%;">
                                                        <el-table-column v-for="col in getEffectiveTableColumns(field)" :key="col.key" :prop="col.key" :label="col.label" :min-width="col.width || 120">
                                                            <template #default="scope">
                                                                <el-select
                                                                    v-if="field.key === 'members' && col.key === 'role'"
                                                                    :model-value="scope.row[col.key]"
                                                                    @update:modelValue="val => updateTableCell(createForm, field.key, scope.$index, col.key, val)"
                                                                    style="width: 100%;"
                                                                    placeholder="请选择角色"
                                                                >
                                                                    <el-option label="负责人" value="leader"></el-option>
                                                                    <el-option label="成员" value="member"></el-option>
                                                                </el-select>
                                                                <el-select
                                                                    v-else-if="field.key === 'members' && col.key === 'college'"
                                                                    :model-value="scope.row[col.key]"
                                                                    @update:modelValue="val => updateTableCell(createForm, field.key, scope.$index, col.key, val)"
                                                                    style="width: 100%;"
                                                                    placeholder="请选择学院"
                                                                    filterable
                                                                >
                                                                    <el-option v-for="opt in colleges" :key="opt" :label="opt" :value="opt"></el-option>
                                                                </el-select>
                                                                <el-select
                                                                    v-else-if="field.key === 'members' && col.key === 'grade'"
                                                                    :model-value="scope.row[col.key]"
                                                                    @update:modelValue="val => updateTableCell(createForm, field.key, scope.$index, col.key, val)"
                                                                    style="width: 100%;"
                                                                    placeholder="请选择年级"
                                                                >
                                                                    <el-option v-for="opt in CNMU_GRADE_OPTIONS" :key="opt" :label="opt" :value="opt"></el-option>
                                                                </el-select>
                                                                <el-select
                                                                    v-else-if="field.key === 'members' && col.key === 'major'"
                                                                    :model-value="scope.row[col.key]"
                                                                    @update:modelValue="val => updateTableCell(createForm, field.key, scope.$index, col.key, val)"
                                                                    style="width: 100%;"
                                                                    placeholder="请选择专业"
                                                                    filterable
                                                                >
                                                                    <el-option v-for="opt in getMemberMajorOptions(scope.row)" :key="opt" :label="opt" :value="opt"></el-option>
                                                                </el-select>
                                                                <el-input
                                                                    v-else
                                                                    :model-value="scope.row[col.key]"
                                                                    @update:modelValue="val => updateTableCell(createForm, field.key, scope.$index, col.key, val)"
                                                                ></el-input>
                                                            </template>
                                                        </el-table-column>
                                                        <el-table-column label="操作" width="80" fixed="right">
                                                            <template #default="scope">
                                                                <el-button type="danger" link size="small" :disabled="field.key === 'members' && isLeaderMemberRow(scope.row)" @click="removeTableRow(createForm, field.key, scope.$index)">删除</el-button>
                                                            </template>
                                                        </el-table-column>
                                                    </el-table>
                                                </div>
                                                <div v-if="field.placeholder && !isCollaboratorsTableField(field)" style="font-size: 12px; color: #999; margin-top: 6px;">{{ field.placeholder }}</div>
                                            </div>

                                            <el-input
                                                v-if="field.type === 'table' && getEffectiveTableColumns(field).length === 0"
                                                type="textarea"
                                                :rows="4"
                                                :model-value="typeof getFieldValue(createForm, field.key) === 'string' ? getFieldValue(createForm, field.key) : JSON.stringify(getFieldValue(createForm, field.key) || [], null, 2)"
                                                @update:modelValue="val => setFieldValue(createForm, field.key, val)"
                                                :placeholder="field.placeholder"></el-input>

                                        </el-form-item>
                                    </el-col>
                                    </template>
                                </el-row>
                            </template>
                        </div>
                        </template>
                    </template>
                    <template v-else>
                        <!-- Fallback for legacy templates -->
                        <div style="text-align: center; color: #999;">表单配置为空，请联系管理员</div>
                    </template>
                        </el-col>
                        <el-col v-if="showJiebangTopicPanel" :span="8">
                            <el-card shadow="never" style="border: 1px solid #ebeef5;">
                                <template #header>
                                    <div style="display:flex; align-items:center; justify-content:space-between;">
                                        <span>揭榜挂帅选题参考</span>
                                        <el-button type="primary" link @click="$router.push('/jiebang-2026')">打开完整指南</el-button>
                                    </div>
                                </template>
                                <el-alert
                                    v-if="String(createForm?.extra_info?.is_jiebang || '').trim() === '是'"
                                    title="已选择“揭榜挂帅”专项，可参考下方选题库。"
                                    type="success"
                                    show-icon
                                    :closable="false"
                                    style="margin-bottom: 10px;"
                                ></el-alert>
                                <el-alert
                                    v-else
                                    title="选择“是否揭榜挂帅：是”时，系统将提示可参考选题库。"
                                    type="info"
                                    show-icon
                                    :closable="false"
                                    style="margin-bottom: 10px;"
                                ></el-alert>
                                <div style="max-height: 560px; overflow: auto;">
                                    <el-skeleton v-if="jiebangTopicsLoading" :rows="8" animated />
                                    <el-empty v-else-if="!jiebangTopicsTree?.groups || jiebangTopicsTree.groups.length === 0" description="暂无选题库"></el-empty>
                                    <el-collapse v-else v-model="jiebangCollapseActive">
                                        <el-collapse-item v-for="g in jiebangTopicsTree.groups" :key="g.group_no" :name="String(g.group_no)">
                                            <template #title>
                                                <span>{{ g.group_no }}. {{ g.group_name }}</span>
                                            </template>
                                            <div v-for="t in (g.topics || [])" :key="t.id" style="margin-bottom: 10px;">
                                                <div style="font-weight: 600; line-height: 20px;">{{ g.group_no }}-{{ t.topic_no }} {{ t.topic_title }}</div>
                                                <div style="color: #666; font-size: 13px; line-height: 18px;">{{ t.topic_desc }}</div>
                                            </div>
                                        </el-collapse-item>
                                    </el-collapse>
                                </div>
                            </el-card>
                        </el-col>
                    </el-row>
                </div>
                
                <!-- 步骤 2 -->
                <div v-if="maxCreateStep >= 1" v-show="activeStep === 1">
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
                <div v-if="maxCreateStep >= 2" v-show="activeStep === 2">
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
                <el-button v-if="activeStep < maxCreateStep" type="primary" @click="nextStep">下一步</el-button>
                <el-button v-if="activeStep === maxCreateStep" type="primary" @click="submitProject" :loading="submitting">提交</el-button>
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
                <el-form-item :label="getField1Label(createUserForm.role)">
                    <el-select v-model="createUserForm.college" :disabled="user?.role === 'college_approver'" filterable style="width: 100%">
                        <el-option v-for="c in getField1Options(createUserForm.role)" :key="c" :label="c" :value="c"></el-option>
                    </el-select>
                </el-form-item>
                <el-form-item :label="getIdentityLabel(createUserForm.role)">
                    <el-input v-model="createUserForm.identity_number" @input="rememberIdentity(createUserForm.role, createUserForm.identity_number)"></el-input>
                </el-form-item>
                <el-form-item :label="getField2Label(createUserForm.role)">
                    <el-select v-model="createUserForm.department" filterable allow-create default-first-option style="width: 100%">
                        <el-option v-for="opt in getField2Options(createUserForm.role, createUserForm.college)" :key="opt" :label="opt" :value="opt"></el-option>
                    </el-select>
                </el-form-item>
                <el-form-item v-if="createUserForm.role === 'teacher'" label="教研室"><el-input v-model="createUserForm.teaching_office"></el-input></el-form-item>
                <el-form-item v-if="createUserForm.role === 'judge'" label="研究领域"><el-input v-model="createUserForm.research_area"></el-input></el-form-item>
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
                <el-form-item :label="getField1Label(editUserForm.role)">
                    <el-select v-model="editUserForm.college" :disabled="user?.role === 'college_approver'" filterable style="width: 100%">
                        <el-option v-for="c in getField1Options(editUserForm.role)" :key="c" :label="c" :value="c"></el-option>
                    </el-select>
                </el-form-item>
                <el-form-item :label="getIdentityLabel(editUserForm.role)">
                    <el-input v-model="editUserForm.identity_number" @input="rememberIdentity(editUserForm.role, editUserForm.identity_number)"></el-input>
                </el-form-item>
                <el-form-item :label="getField2Label(editUserForm.role)">
                    <el-select v-model="editUserForm.department" filterable allow-create default-first-option style="width: 100%">
                        <el-option v-for="opt in getField2Options(editUserForm.role, editUserForm.college)" :key="opt" :label="opt" :value="opt"></el-option>
                    </el-select>
                </el-form-item>
                <el-form-item v-if="editUserForm.role === 'teacher'" label="教研室"><el-input v-model="editUserForm.teaching_office"></el-input></el-form-item>
                <el-form-item v-if="editUserForm.role === 'judge'" label="研究领域"><el-input v-model="editUserForm.research_area"></el-input></el-form-item>
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

        <el-dialog v-model="showAdvisorReviewDialog" title="指导教师初审" width="600px">
            <el-form :model="advisorReviewForm" label-width="100px" v-if="currentAdvisorProject">
                <div style="margin-bottom: 20px; padding: 15px; background: #f8f9fa; border-radius: 4px;">
                    <p><strong>项目名称：</strong>{{ currentAdvisorProject.title }}</p>
                    <p><strong>作品类别：</strong>{{ getProjectTypeLabel(currentAdvisorProject.project_type) }}</p>
                    <p><strong>申报学院：</strong>{{ currentAdvisorProject.college }}</p>
                </div>
                <el-form-item label="初审结果" required>
                    <el-radio-group v-model="advisorReviewForm.status">
                        <el-radio label="pass">通过（进入学院赛）</el-radio>
                        <el-radio label="reject">驳回（需要修改）</el-radio>
                    </el-radio-group>
                </el-form-item>
                <el-form-item label="审核意见" required>
                    <el-input type="textarea" v-model="advisorReviewForm.opinion" :rows="3" placeholder="请填写审核意见"></el-input>
                </el-form-item>
            </el-form>
            <template #footer>
                <el-button @click="showAdvisorReviewDialog = false">取消</el-button>
                <el-button type="primary" @click="submitAdvisorReview" :loading="submittingAdvisorReview">提交审核</el-button>
            </template>
        </el-dialog>

        <!-- 审核/详情弹窗 -->
        <el-dialog v-model="showDetailDialog" :title="currentProject?.title" width="900px" top="5vh">
            <div v-if="currentProject">
                <el-tabs v-model="detailActiveTab">
                    <!-- Tab 1: 基本信息 -->
                    <el-tab-pane label="报名信息" name="basic">
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
                            <template v-if="currentProject.form_config?.groups && currentProject.form_config.groups.length > 0">
                                <template v-for="(group, gIndex) in currentProject.form_config.groups" :key="gIndex">
                                    <div v-if="shouldShow(currentProject, group)">
                                        <el-divider v-if="group.title" content-position="left">{{ group.title }}</el-divider>
                                        <template v-if="isAdvisorGroup(group)">
                                            <template v-if="Array.isArray(currentProject.extra_info?.advisors) && currentProject.extra_info.advisors.length > 0">
                                                <el-card v-for="(a, idx) in currentProject.extra_info.advisors" :key="idx" shadow="never" style="margin-bottom: 12px;">
                                                    <template #header>
                                                        <div style="display: flex; justify-content: space-between; align-items: center;">
                                                            <span>指导教师{{ idx + 1 }}（{{ getAdvisorRankLabel(idx) }}）</span>
                                                        </div>
                                                    </template>
                                                    <el-form-item label="主次标识">
                                                        <el-radio-group :model-value="idx" disabled>
                                                            <el-radio :label="0">第一指导教师</el-radio>
                                                            <el-radio :label="1">第二指导教师</el-radio>
                                                            <el-radio :label="2">第三指导教师</el-radio>
                                                        </el-radio-group>
                                                    </el-form-item>
                                                    <el-row :gutter="20">
                                                        <el-col :span="12">
                                                            <el-form-item label="姓名">
                                                                <el-input v-model="a.name" disabled></el-input>
                                                            </el-form-item>
                                                        </el-col>
                                                        <el-col :span="12">
                                                            <el-form-item label="职称">
                                                                <el-input v-model="a.title" disabled></el-input>
                                                            </el-form-item>
                                                        </el-col>
                                                    </el-row>
                                                    <el-row :gutter="20">
                                                        <el-col :span="12">
                                                            <el-form-item label="所在单位">
                                                                <el-input v-model="a.org" disabled></el-input>
                                                            </el-form-item>
                                                        </el-col>
                                                        <el-col :span="12">
                                                            <el-form-item label="指导类型">
                                                                <el-input v-model="a.guidance_type" disabled></el-input>
                                                            </el-form-item>
                                                        </el-col>
                                                    </el-row>
                                                    <el-row :gutter="20">
                                                        <el-col :span="12">
                                                            <el-form-item label="研究领域">
                                                                <el-input v-model="a.research_area" disabled></el-input>
                                                            </el-form-item>
                                                        </el-col>
                                                        <el-col :span="12">
                                                            <el-form-item label="联系电话">
                                                                <el-input v-model="a.phone" disabled></el-input>
                                                            </el-form-item>
                                                        </el-col>
                                                    </el-row>
                                                </el-card>
                                            </template>
                                            <template v-else>
                                                <el-card shadow="never" style="margin-bottom: 12px;">
                                                    <template #header>
                                                        <div style="display: flex; justify-content: space-between; align-items: center;">
                                                            <span>指导教师（第一指导教师）</span>
                                                        </div>
                                                    </template>
                                                    <el-row :gutter="20">
                                                        <el-col :span="12">
                                                            <el-form-item label="姓名">
                                                                <el-input :model-value="currentProject.advisor_name" disabled></el-input>
                                                            </el-form-item>
                                                        </el-col>
                                                        <el-col :span="12">
                                                            <el-form-item label="职称">
                                                                <el-input :model-value="currentProject.extra_info?.advisor_info?.title || currentProject.extra_info?.advisor_title" disabled></el-input>
                                                            </el-form-item>
                                                        </el-col>
                                                    </el-row>
                                                    <el-row :gutter="20">
                                                        <el-col :span="12">
                                                            <el-form-item label="所在单位">
                                                                <el-input :model-value="currentProject.extra_info?.advisor_info?.dept || currentProject.extra_info?.advisor_unit" disabled></el-input>
                                                            </el-form-item>
                                                        </el-col>
                                                        <el-col :span="12">
                                                            <el-form-item label="指导类型">
                                                                <el-input :model-value="'校内导师'" disabled></el-input>
                                                            </el-form-item>
                                                        </el-col>
                                                    </el-row>
                                                    <el-row :gutter="20">
                                                        <el-col :span="12">
                                                            <el-form-item label="研究领域">
                                                                <el-input :model-value="currentProject.extra_info?.advisor_research" disabled></el-input>
                                                            </el-form-item>
                                                        </el-col>
                                                        <el-col :span="12">
                                                            <el-form-item label="联系电话">
                                                                <el-input :model-value="currentProject.extra_info?.advisor_info?.phone || currentProject.extra_info?.advisor_phone" disabled></el-input>
                                                            </el-form-item>
                                                        </el-col>
                                                    </el-row>
                                                </el-card>
                                            </template>
                                        </template>
                                        <template v-else>
                                            <el-row :gutter="20">
                                                <template v-for="(field, fIndex) in group.fields" :key="fIndex">
                                                    <el-col v-if="shouldShow(currentProject, field)" :span="field.type === 'textarea' || field.type === 'richtext' || field.type === 'table' ? 24 : 12">
                                                        <el-form-item :label="field.label">
                                                            <el-input
                                                                v-if="field.type === 'text'"
                                                                :model-value="getFieldValue(currentProject, field.key)"
                                                                :placeholder="field.placeholder"
                                                                disabled></el-input>

                                                            <el-input
                                                                v-if="field.type === 'textarea'"
                                                                type="textarea"
                                                                :rows="3"
                                                                :model-value="getFieldValue(currentProject, field.key)"
                                                                :placeholder="field.placeholder"
                                                                disabled></el-input>

                                                            <el-input
                                                                v-if="field.type === 'richtext'"
                                                                type="textarea"
                                                                :rows="6"
                                                                :model-value="getFieldValue(currentProject, field.key)"
                                                                :placeholder="field.placeholder"
                                                                disabled></el-input>

                                                            <el-select
                                                                v-if="field.type === 'select'"
                                                                :model-value="getFieldValue(currentProject, field.key)"
                                                                style="width: 100%"
                                                                :placeholder="field.placeholder"
                                                                disabled
                                                                :filterable="true">
                                                                <template v-if="field.key === 'project_type'">
                                                                    <el-option v-for="t in allowedProjectTypes" :key="t.value" :label="t.label" :value="t.value"></el-option>
                                                                </template>
                                                                <template v-else-if="field.key === 'college'">
                                                                    <el-option v-for="c in colleges" :key="c" :label="c" :value="c"></el-option>
                                                                </template>
                                                                <template v-else-if="field.key === 'department' || String(field.key).endsWith('.department')">
                                                                    <el-option v-for="m in getMajorsByCollege(getFieldValue(currentProject, 'extra_info.leader_info.college') || getFieldValue(currentProject, 'college'))" :key="m" :label="m" :value="m"></el-option>
                                                                </template>
                                                                <template v-else-if="field.key === 'inspiration_source'">
                                                                    <el-option v-for="item in inspirationOptions" :key="item.value" :label="item.label" :value="item.value">
                                                                        <span style="float: left">{{ item.label }}</span>
                                                                        <span style="float: right; color: #8492a6; font-size: 13px">{{ item.summary ? item.summary.substring(0, 20) + '...' : '' }}</span>
                                                                    </el-option>
                                                                </template>
                                                                <template v-else>
                                                                    <el-option v-for="opt in field.options" :key="opt.value" :label="opt.label" :value="opt.value"></el-option>
                                                                </template>
                                                            </el-select>

                                                            <el-date-picker
                                                                v-if="field.type === 'date'"
                                                                :model-value="getFieldValue(currentProject, field.key)"
                                                                type="date"
                                                                value-format="YYYY-MM-DD"
                                                                style="width: 100%"
                                                                :placeholder="field.placeholder"
                                                                disabled></el-date-picker>

                                                            <el-input-number
                                                                v-if="field.type === 'number'"
                                                                :model-value="getFieldValue(currentProject, field.key)"
                                                                style="width: 100%"
                                                                :min="0"
                                                                disabled></el-input-number>

                                                            <el-radio-group
                                                                v-if="field.type === 'radio'"
                                                                :model-value="getFieldValue(currentProject, field.key)"
                                                                disabled>
                                                                <el-radio v-for="opt in field.options" :key="opt.value" :label="opt.value">{{ opt.label }}</el-radio>
                                                            </el-radio-group>

                                                            <el-checkbox-group
                                                                v-if="field.type === 'checkbox'"
                                                                :model-value="Array.isArray(getFieldValue(currentProject, field.key)) ? getFieldValue(currentProject, field.key) : []"
                                                                disabled>
                                                                <el-checkbox v-for="opt in field.options" :key="opt.value" :label="opt.value">{{ opt.label }}</el-checkbox>
                                                            </el-checkbox-group>

                                                            <div v-if="field.type === 'file'">
                                                                <div v-if="getFieldValue(currentProject, field.key)" style="margin-top: 5px;">
                                                                    <el-tag type="success" style="margin-right: 10px;">已上传</el-tag>
                                                                    <el-link :href="getFieldValue(currentProject, field.key)" target="_blank" type="primary" style="margin-right: 10px;">查看</el-link>
                                                                </div>
                                                                <div v-else style="margin-top: 5px;">未上传</div>
                                                                <div v-if="field.placeholder" style="font-size: 12px; color: #999;">{{ field.placeholder }}</div>
                                                            </div>

                                                            <div v-if="field.type === 'table' && getEffectiveTableColumns(field).length > 0">
                                                                <el-table
                                                                    :data="getTableRows(currentProject, field.key)"
                                                                    border
                                                                    size="small"
                                                                    style="width: 100%;">
                                                                    <el-table-column
                                                                        v-for="col in getEffectiveTableColumns(field).filter(c => c.key !== '操作')"
                                                                        :key="col.key"
                                                                        :prop="col.key"
                                                                        :label="col.label"
                                                                        :min-width="col.width || 120">
                                                                        <template #default="scope">
                                                                            <el-input :model-value="scope.row[col.key]" disabled size="small"></el-input>
                                                                        </template>
                                                                    </el-table-column>
                                                                </el-table>
                                                            </div>
                                                        </el-form-item>
                                                    </el-col>
                                                </template>
                                            </el-row>
                                        </template>
                                    </div>
                                </template>
                            </template>
                            <template v-else-if="currentProject.template_type === 'startup'">
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
                                <template v-if="Array.isArray(currentProject.extra_info?.advisors) && currentProject.extra_info.advisors.length > 0">
                                    <div v-for="(a, idx) in currentProject.extra_info.advisors" :key="idx" style="margin-bottom: 12px;">
                                        <el-row :gutter="20">
                                            <el-col :span="8"><el-form-item label="姓名"><el-input :model-value="a.name"></el-input></el-form-item></el-col>
                                            <el-col :span="8"><el-form-item label="职称"><el-input :model-value="a.title"></el-input></el-form-item></el-col>
                                            <el-col :span="8"><el-form-item label="所在单位"><el-input :model-value="a.org"></el-input></el-form-item></el-col>
                                        </el-row>
                                        <el-row :gutter="20">
                                            <el-col :span="8"><el-form-item label="指导类型"><el-input :model-value="a.guidance_type"></el-input></el-form-item></el-col>
                                            <el-col :span="8"><el-form-item label="研究领域"><el-input :model-value="a.research_area"></el-input></el-form-item></el-col>
                                            <el-col :span="8"><el-form-item label="联系电话"><el-input :model-value="a.phone"></el-input></el-form-item></el-col>
                                        </el-row>
                                    </div>
                                </template>
                                <template v-else>
                                    <el-row :gutter="20">
                                        <el-col :span="8"><el-form-item label="姓名"><el-input :model-value="currentProject.advisor_name"></el-input></el-form-item></el-col>
                                        <el-col :span="8"><el-form-item label="部门"><el-input :model-value="currentProject.extra_info?.advisor_info?.dept"></el-input></el-form-item></el-col>
                                        <el-col :span="8"><el-form-item label="职称"><el-input :model-value="currentProject.extra_info?.advisor_info?.title"></el-input></el-form-item></el-col>
                                    </el-row>
                                    <el-row :gutter="20">
                                        <el-col :span="12"><el-form-item label="电话"><el-input :model-value="currentProject.extra_info?.advisor_info?.phone"></el-input></el-form-item></el-col>
                                        <el-col :span="12"><el-form-item label="邮箱"><el-input :model-value="currentProject.extra_info?.advisor_info?.email"></el-input></el-form-item></el-col>
                                    </el-row>
                                </template>
                                
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
                    <el-tab-pane label="项目详情" name="details" v-if="!currentProject.form_config?.groups || currentProject.form_config.groups.length === 0 || currentProject.template_type === 'startup'">
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

                    <el-tab-pane v-if="currentProject.template_type === 'training'" label="升级申请" name="upgrade">
                        <div style="margin-bottom: 10px;">
                            <el-tag>当前级别：{{ getProjectLevelText(currentProject.level) }}</el-tag>
                            <el-tag v-if="hasPendingUpgradeRequest()" type="warning" style="margin-left: 6px;">有待处理申请</el-tag>
                        </div>
                        <el-button
                            v-if="user?.role === 'student' && canApplyUpgrade(currentProject)"
                            type="primary"
                            size="small"
                            style="margin-bottom: 10px;"
                            @click="openUpgradeDialog(currentProject)">
                            申请升级
                        </el-button>
                        <el-table :data="upgradeRequests" border size="small" v-loading="upgradeRequestsLoading">
                            <el-table-column prop="created_at" label="申请时间" width="170"></el-table-column>
                            <el-table-column label="升级方向" width="160">
                                <template #default="scope">
                                    {{ getProjectLevelText(scope.row.from_level) }} → {{ getProjectLevelText(scope.row.to_level) }}
                                </template>
                            </el-table-column>
                            <el-table-column label="状态" width="100">
                                <template #default="scope">
                                    <el-tag :type="scope.row.status === 'approved' ? 'success' : (scope.row.status === 'rejected' ? 'danger' : 'warning')">
                                        {{ scope.row.status === 'approved' ? '通过' : (scope.row.status === 'rejected' ? '驳回' : '待处理') }}
                                    </el-tag>
                                </template>
                            </el-table-column>
                            <el-table-column prop="review_comment" label="审核意见"></el-table-column>
                            <el-table-column v-if="canReviewUpgradeRequests()" label="操作" width="160">
                                <template #default="scope">
                                    <el-button v-if="scope.row.status === 'pending'" size="small" type="success" @click="reviewUpgradeRequest(scope.row.id, 'approved')">通过</el-button>
                                    <el-button v-if="scope.row.status === 'pending'" size="small" type="danger" @click="reviewUpgradeRequest(scope.row.id, 'rejected')">驳回</el-button>
                                </template>
                            </el-table-column>
                        </el-table>
                    </el-tab-pane>

                    <el-tab-pane v-if="canViewAdminReview()" label="后台评审/获奖" name="admin_review">
                        <el-form :model="adminReviewForm" label-width="140px">
                            <el-row :gutter="20">
                                <el-col :span="12">
                                    <el-form-item label="当前竞赛阶段">
                                        <el-select v-model="adminReviewForm.review_stage" style="width:100%" :disabled="!canEditAdminField('review_stage')">
                                            <el-option label="校赛" value="school"></el-option>
                                            <el-option label="省赛" value="provincial"></el-option>
                                            <el-option label="国赛" value="national"></el-option>
                                        </el-select>
                                    </el-form-item>
                                </el-col>
                                <el-col :span="12">
                                    <el-form-item label="学院赛评审结果">
                                        <el-select v-model="adminReviewForm.college_review_result" style="width:100%" :disabled="!canEditAdminField('college_review_result')">
                                            <el-option label="待评审" value="pending"></el-option>
                                            <el-option label="通过" value="approved"></el-option>
                                            <el-option label="不通过" value="rejected"></el-option>
                                        </el-select>
                                    </el-form-item>
                                </el-col>
                            </el-row>
                            <el-row :gutter="20">
                                <el-col :span="12">
                                    <el-form-item label="校赛评审结果">
                                        <el-select v-model="adminReviewForm.school_review_result" style="width:100%" :disabled="!canEditAdminField('school_review_result')">
                                            <el-option label="待评审" value="pending"></el-option>
                                            <el-option label="通过" value="approved"></el-option>
                                            <el-option label="不通过" value="rejected"></el-option>
                                        </el-select>
                                    </el-form-item>
                                </el-col>
                                <el-col :span="12">
                                    <el-form-item label="省赛获奖等级">
                                        <el-select v-model="adminReviewForm.provincial_award_level" style="width:100%" :disabled="!canEditAdminField('provincial_award_level')">
                                            <el-option label="特等" value="special"></el-option>
                                            <el-option label="一等" value="first"></el-option>
                                            <el-option label="二等" value="second"></el-option>
                                            <el-option label="三等" value="third"></el-option>
                                            <el-option label="优秀奖" value="excellent"></el-option>
                                            <el-option label="无" value="none"></el-option>
                                        </el-select>
                                    </el-form-item>
                                </el-col>
                            </el-row>
                            <el-row :gutter="20">
                                <el-col :span="12">
                                    <el-form-item label="国赛获奖等级">
                                        <el-select v-model="adminReviewForm.national_award_level" style="width:100%" :disabled="!canEditAdminField('national_award_level')">
                                            <el-option label="金奖" value="gold"></el-option>
                                            <el-option label="银奖" value="silver"></el-option>
                                            <el-option label="铜奖" value="bronze"></el-option>
                                            <el-option label="特等" value="special"></el-option>
                                            <el-option label="一等" value="first"></el-option>
                                            <el-option label="二等" value="second"></el-option>
                                            <el-option label="三等" value="third"></el-option>
                                            <el-option label="优秀奖" value="excellent"></el-option>
                                            <el-option label="无" value="none"></el-option>
                                        </el-select>
                                    </el-form-item>
                                </el-col>
                            </el-row>
                            <el-form-item label="科研管理部门意见">
                                <el-input v-model="adminReviewForm.research_admin_opinion" type="textarea" :rows="3" :disabled="!canEditAdminField('research_admin_opinion')"></el-input>
                            </el-form-item>
                            <el-form-item label="院系负责人或导师意见">
                                <el-input v-model="adminReviewForm.department_head_opinion" type="textarea" :rows="3" :disabled="!canEditAdminField('department_head_opinion')"></el-input>
                            </el-form-item>
                            <el-form-item>
                                <el-button type="primary" @click="saveAdminReview" :loading="adminReviewSaving" :disabled="!canEditAdminField('review_stage') && !canEditAdminField('college_review_result') && !canEditAdminField('school_review_result') && !canEditAdminField('provincial_award_level') && !canEditAdminField('national_award_level') && !canEditAdminField('research_admin_opinion') && !canEditAdminField('department_head_opinion')">
                                    保存
                                </el-button>
                            </el-form-item>
                        </el-form>

                        <el-divider content-position="left">获奖记录</el-divider>
                        <div style="margin-bottom: 10px;">
                            <el-button v-if="canManageAwards" type="primary" size="small" @click="openAwardDialog()">新增获奖记录</el-button>
                        </div>
                        <el-table :data="projectAwards" border size="small" v-loading="projectAwardsLoading">
                            <el-table-column prop="stage" label="阶段" width="90">
                                <template #default="scope">{{ getReviewStageText(scope.row.stage) }}</template>
                            </el-table-column>
                            <el-table-column prop="award_level" label="等级" width="120">
                                <template #default="scope">{{ getAwardLevelText(scope.row.award_level) }}</template>
                            </el-table-column>
                            <el-table-column prop="award_name" label="奖项名称" min-width="160"></el-table-column>
                            <el-table-column prop="award_time" label="获奖时间" width="120"></el-table-column>
                            <el-table-column prop="issuer" label="颁奖单位" min-width="160"></el-table-column>
                            <el-table-column prop="created_at" label="录入时间" width="170"></el-table-column>
                            <el-table-column v-if="canManageAwards" label="操作" width="140" fixed="right">
                                <template #default="scope">
                                    <el-button size="small" @click="openAwardDialog(scope.row)">编辑</el-button>
                                    <el-button size="small" type="danger" @click="deleteAward(scope.row.id)">删除</el-button>
                                </template>
                            </el-table-column>
                        </el-table>
                    </el-tab-pane>

                    <el-tab-pane v-if="user?.role === 'school_approver'" label="省赛/国赛结果" name="pn_results">
                        <el-form :model="pnResultForm" label-width="160px">
                            <el-divider content-position="left">省赛</el-divider>
                            <el-row :gutter="20">
                                <el-col :span="12">
                                    <el-form-item label="省赛状态">
                                        <el-select v-model="pnResultForm.provincial_status" style="width:100%">
                                            <el-option label="未参赛" value="未参赛"></el-option>
                                            <el-option label="已参赛" value="已参赛"></el-option>
                                            <el-option label="已获奖" value="已获奖"></el-option>
                                        </el-select>
                                    </el-form-item>
                                </el-col>
                                <el-col :span="12">
                                    <el-form-item label="省赛获奖等级">
                                        <el-select v-model="pnResultForm.provincial_award_level" style="width:100%" placeholder="请选择或输入" filterable allow-create clearable>
                                            <el-option v-for="opt in getAwardOptionsWithCurrent(currentProject, 'provincial_award_level')" :key="opt" :label="getAwardLevelLabel(opt) || opt" :value="opt"></el-option>
                                            <el-option label="无" value="none"></el-option>
                                        </el-select>
                                    </el-form-item>
                                </el-col>
                            </el-row>
                            <el-row :gutter="20">
                                <el-col :span="12">
                                    <el-form-item label="获奖证书编号">
                                        <el-input v-model="pnResultForm.provincial_certificate_no" placeholder="请输入证书编号"></el-input>
                                    </el-form-item>
                                </el-col>
                                <el-col :span="12">
                                    <el-form-item label="是否晋级国赛">
                                        <el-switch v-model="pnResultForm.provincial_advance_national" active-text="是" inactive-text="否"></el-switch>
                                    </el-form-item>
                                </el-col>
                            </el-row>
                            <el-form-item label="省赛评审意见">
                                <el-input v-model="pnResultForm.provincial_review_comment" type="textarea" :rows="3"></el-input>
                            </el-form-item>

                            <el-divider content-position="left">国赛</el-divider>
                            <el-row :gutter="20">
                                <el-col :span="12">
                                    <el-form-item label="国赛状态">
                                        <el-select v-model="pnResultForm.national_status" style="width:100%">
                                            <el-option label="未参赛" value="未参赛"></el-option>
                                            <el-option label="已参赛" value="已参赛"></el-option>
                                            <el-option label="已获奖" value="已获奖"></el-option>
                                        </el-select>
                                    </el-form-item>
                                </el-col>
                                <el-col :span="12">
                                    <el-form-item label="国赛获奖等级">
                                        <el-select v-model="pnResultForm.national_award_level" style="width:100%" placeholder="请选择或输入" filterable allow-create clearable>
                                            <el-option v-for="opt in getAwardOptionsWithCurrent(currentProject, 'national_award_level')" :key="opt" :label="getAwardLevelLabel(opt) || opt" :value="opt"></el-option>
                                            <el-option label="无" value="none"></el-option>
                                        </el-select>
                                    </el-form-item>
                                </el-col>
                            </el-row>
                            <el-row :gutter="20">
                                <el-col :span="12">
                                    <el-form-item label="国赛获奖证书编号">
                                        <el-input v-model="pnResultForm.national_certificate_no" placeholder="请输入证书编号"></el-input>
                                    </el-form-item>
                                </el-col>
                            </el-row>
                            <el-form-item label="国赛评审意见">
                                <el-input v-model="pnResultForm.national_review_comment" type="textarea" :rows="3"></el-input>
                            </el-form-item>

                            <el-form-item>
                                <el-button type="primary" @click="savePnResults" :loading="pnResultSaving">保存</el-button>
                            </el-form-item>
                        </el-form>
                    </el-tab-pane>



                    <!-- Tab 3.5: 过程管理 -->
                    <el-tab-pane label="过程管理" name="process" v-if="currentProject && (user?.role === 'student' || ['project_admin', 'system_admin', 'school_approver', 'college_approver', 'teacher', 'judge'].includes(user?.role))">
                        <el-skeleton v-if="projectProcessLoading" :rows="6" animated></el-skeleton>
                        <template v-else-if="projectProcess && projectProcess.template_name && Array.isArray(projectProcess.process_structure) && projectProcess.process_structure.length > 0">
                            <!-- 顶置进度条 -->
                            <el-steps :active="getProcessActiveStep()" finish-status="success" style="margin-bottom: 30px;">
                                <el-step v-for="node in projectProcess.process_structure" :key="node" :title="node"></el-step>
                            </el-steps>

                            <el-card v-if="shouldShowCollegeRecommendationPanel()" style="margin-bottom: 20px;">
                                <h4 style="margin:0 0 10px 0;">学院评审录入（创新训练项目）</h4>
                                <el-alert type="warning" :closable="false" style="margin-bottom: 12px;">
                                    <template #title>学院推荐截止时间：4月30日</template>
                                </el-alert>
                                <el-form label-width="120px">
                                    <el-form-item label="资格审核结果">
                                        <el-radio-group v-model="collegeRecForm.passed">
                                            <el-radio :label="true">通过</el-radio>
                                            <el-radio :label="false">不通过</el-radio>
                                        </el-radio-group>
                                    </el-form-item>
                                    <el-form-item label="审核意见">
                                        <el-input v-model="collegeRecForm.feedback" type="textarea" :rows="2" placeholder="资格审核意见/答辩意见/排序说明"></el-input>
                                    </el-form-item>
                                    <el-form-item>
                                        <el-button size="small" type="primary" :loading="collegeRecSaving" @click="submitCollegeRecommendation('qualification')">提交资格审核</el-button>
                                    </el-form-item>
                                    <el-divider></el-divider>
                                    <el-form-item label="评审答辩成绩">
                                        <el-input v-model="collegeRecForm.defense_score" placeholder="如 85.5"></el-input>
                                    </el-form-item>
                                    <el-form-item>
                                        <el-button size="small" type="primary" :loading="collegeRecSaving" @click="submitCollegeRecommendation('defense')">提交答辩成绩</el-button>
                                    </el-form-item>
                                    <el-divider></el-divider>
                                    <el-form-item label="推荐排序">
                                        <el-input v-model="collegeRecForm.recommend_rank" placeholder="1,2,3..."></el-input>
                                    </el-form-item>
                                    <el-form-item label="重点支持项目">
                                        <el-switch v-model="collegeRecForm.is_key_support"></el-switch>
                                    </el-form-item>
                                    <el-form-item>
                                        <el-button size="small" type="primary" :loading="collegeRecSaving" @click="submitCollegeRecommendation('ranking')">提交排序与推荐</el-button>
                                    </el-form-item>
                                </el-form>
                            </el-card>
                            
                            <el-timeline>
                                <el-timeline-item v-for="(node, index) in projectProcess.process_structure" :key="node" placement="top" :type="isProcessNodeUnlocked(index) ? 'primary' : 'info'">
                                    <el-card :style="!isProcessNodeUnlocked(index) ? 'opacity: 0.6; pointer-events: none;' : ''">
                                        <h4>
                                            {{ node }}
                                            <el-tag v-if="!isProcessNodeUnlocked(index)" size="small" type="info" style="margin-left: 10px;">未解锁</el-tag>
                                            <el-tag v-else-if="isProcessNodeCompleted(node)" size="small" type="success" style="margin-left: 10px;">
                                                {{ projectProcess.node_current_status[node] }}
                                            </el-tag>
                                            <el-tag v-else size="small" type="warning" style="margin-left: 10px;">当前阶段</el-tag>
                                        </h4>
                                        <el-form label-width="90px" v-if="isProcessNodeUnlocked(index)">
                                            <el-form-item label="状态">
                                                <el-select v-model="projectProcess.node_current_status[node]" style="width: 100%" :disabled="!canEditProcessNodeFor(node)">
                                                    <el-option v-for="opt in (projectProcess.node_status_options && projectProcess.node_status_options[node] ? projectProcess.node_status_options[node] : [])" :key="opt" :label="opt" :value="opt"></el-option>
                                                </el-select>
                                            </el-form-item>
                                            <el-form-item label="获奖等级" v-if="projectProcess.node_current_status[node] === '已获奖' && projectProcess.award_levels && projectProcess.award_levels.length > 0">
                                                <el-select v-model="projectProcess.node_award_levels[node]" style="width: 100%" :disabled="!canEditProcessNodeFor(node)">
                                                    <el-option v-for="level in projectProcess.award_levels" :key="level" :label="level" :value="level"></el-option>
                                                </el-select>
                                            </el-form-item>
                                            <el-form-item label="意见">
                                                <el-input v-model="projectProcess.node_comments[node]" type="textarea" :rows="2" :disabled="!canEditProcessNodeFor(node)"></el-input>
                                            </el-form-item>
                                            <el-form-item v-if="canEditProcessNodeFor(node)">
                                                <el-button size="small" type="primary" @click="saveProcessNode(node)" :loading="projectProcessSaving[node]">保存</el-button>
                                            </el-form-item>
                                        </el-form>
                                    </el-card>
                                </el-timeline-item>
                            </el-timeline>
                        </template>
                        <div v-if="shouldShowProcessMaterials()">
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
                        </div>
                        <el-empty v-if="!projectProcess || !projectProcess.template_name || !Array.isArray(projectProcess.process_structure) || projectProcess.process_structure.length === 0" description="暂无过程配置"></el-empty>
                    </el-tab-pane>

                    <!-- Tab 4: 结题成果归集与经验提交 -->
                    <el-tab-pane label="结题成果归集与经验提交" name="audit">
                         <div class="project-detail">
                            <div style="margin-bottom: 12px;">
                                <div style="font-weight: bold; font-size: 18px;">结题成果归集与经验提交</div>
                                <div style="color:#666; margin-top: 6px;">本项目为“挑战杯”大挑参赛项目，已获奖并结题，请完善用于沉淀至“往届项目经验库”的核心内容，严格符合大挑成果规范。</div>
                            </div>

                            <el-descriptions :column="2" border>
                                <el-descriptions-item label="当前项目状态">{{ getStatusTextForRow(currentProject) }}</el-descriptions-item>
                                <el-descriptions-item label="作品类别">
                                    <el-tag effect="plain">{{ getWorkCategoryLabel(currentProject.extra_info?.work_category) || '—' }}</el-tag>
                                </el-descriptions-item>
                                <el-descriptions-item label="当前审核状态">
                                    <el-tag :type="getLegacyAuditTagType()" effect="light">
                                        {{ getLegacyAuditText() }}
                                    </el-tag>
                                    <span v-if="currentProject.extra_info?.methodology_submitted_at" style="margin-left: 10px; color:#666;">{{ currentProject.extra_info.methodology_submitted_at }}</span>
                                </el-descriptions-item>
                            </el-descriptions>

                            <div class="mt-4">
                                <h4>项目材料</h4>
                                <el-table :data="getExperienceMaterialRows()" border size="small">
                                    <el-table-column prop="name" label="材料类型" width="160"></el-table-column>
                                    <el-table-column prop="desc" label="说明">
                                        <template #default="scope">
                                            <div style="white-space: pre-wrap;">{{ scope.row.desc }}</div>
                                        </template>
                                    </el-table-column>
                                    <el-table-column label="操作" width="140">
                                        <template #default="scope">
                                            <el-button v-if="scope.row.url" link type="primary" @click="openUrl(scope.row.url)">下载/查看</el-button>
                                            <span v-else style="color:#999;">暂无</span>
                                        </template>
                                    </el-table-column>
                                </el-table>
                            </div>

                            <div class="mt-4">
                                <h4>大挑评审专家评语（自动收集，已脱敏）</h4>
                                <div style="color:#666; margin-bottom: 8px;">来自大挑院级/校级盲评阶段的评委专业评价，已隐去评委姓名、单位等身份信息</div>
                                <el-empty v-if="getDachuangExpertReviews().length === 0" description="暂无大挑评审评语（该项目未完成大挑盲评或无评审记录）"></el-empty>
                                <el-table v-else :data="getDachuangExpertReviews()" border size="small">
                                    <el-table-column label="评委" width="120">
                                        <template #default>评委</template>
                                    </el-table-column>
                                    <el-table-column prop="score" label="评分" width="100"></el-table-column>
                                    <el-table-column prop="comment" label="评语"></el-table-column>
                                </el-table>
                            </div>

                            <div class="mt-4" style="background-color: #f9fafb; padding: 15px; border-radius: 4px; border: 1px solid #eaeaea;">
                                <div style="display:flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap;">
                                    <h4 style="margin:0;">方法论总结（富文本）</h4>
                                    <div style="display:flex; gap: 8px; flex-wrap: wrap;">
                                        <el-button size="small" @click="formatEditor('bold')">加粗</el-button>
                                        <el-button size="small" @click="formatEditor('italic')">斜体</el-button>
                                        <el-button size="small" @click="formatEditor('underline')">下划线</el-button>
                                        <el-button size="small" @click="formatEditor('insertUnorderedList')">列表</el-button>
                                    </div>
                                </div>
                                
                                <div style="margin-top: 12px;">
                                    <div style="font-weight: 600; margin-bottom: 6px;">模块1：选题背景与科学问题（100字）→ 对应科学性</div>
                                    <div class="rich-editor" contenteditable="true" :data-key="'bg'" @focus="activeEditorKey='bg'" @input="onEditorInput('bg', $event)" v-html="methodologySections.bg" style="min-height: 90px; padding: 10px; border: 1px solid #ddd; border-radius: 4px; background: #fff;"></div>
                                    <div style="color:#666; font-size: 12px; margin-top: 4px;">已输入 {{ getEditorTextLen('bg') }} 字 / 上限 {{ getEditorLimit('bg') }} 字</div>
                                </div>
                                
                                <div style="margin-top: 12px;">
                                    <div style="font-weight: 600; margin-bottom: 6px;">模块2：研究/设计方法与过程（150字）→ 对应科学性</div>
                                    <div class="rich-editor" contenteditable="true" :data-key="'process'" @focus="activeEditorKey='process'" @input="onEditorInput('process', $event)" v-html="methodologySections.process" style="min-height: 110px; padding: 10px; border: 1px solid #ddd; border-radius: 4px; background: #fff;"></div>
                                    <div style="color:#666; font-size: 12px; margin-top: 4px;">已输入 {{ getEditorTextLen('process') }} 字 / 上限 {{ getEditorLimit('process') }} 字</div>
                                </div>
                                
                                <div style="margin-top: 12px;">
                                    <div style="font-weight: 600; margin-bottom: 6px;">模块3：核心创新点与突破（100字）→ 对应先进性</div>
                                    <div class="rich-editor" contenteditable="true" :data-key="'innovation'" @focus="activeEditorKey='innovation'" @input="onEditorInput('innovation', $event)" v-html="methodologySections.innovation" style="min-height: 90px; padding: 10px; border: 1px solid #ddd; border-radius: 4px; background: #fff;"></div>
                                    <div style="color:#666; font-size: 12px; margin-top: 4px;">已输入 {{ getEditorTextLen('innovation') }} 字 / 上限 {{ getEditorLimit('innovation') }} 字</div>
                                </div>
                                
                                <div style="margin-top: 12px;">
                                    <div style="font-weight: 600; margin-bottom: 6px;">模块4：应用价值与实践前景（100字）→ 对应应用价值</div>
                                    <div class="rich-editor" contenteditable="true" :data-key="'effect'" @focus="activeEditorKey='effect'" @input="onEditorInput('effect', $event)" v-html="methodologySections.effect" style="min-height: 90px; padding: 10px; border: 1px solid #ddd; border-radius: 4px; background: #fff;"></div>
                                    <div style="color:#666; font-size: 12px; margin-top: 4px;">已输入 {{ getEditorTextLen('effect') }} 字 / 上限 {{ getEditorLimit('effect') }} 字</div>
                                </div>
                                
                                <div style="margin-top: 12px;">
                                    <div style="font-weight: 600; margin-bottom: 6px;">模块5：规范性说明（50字）→ 对应规范性</div>
                                    <div class="rich-editor" contenteditable="true" :data-key="'norm'" @focus="activeEditorKey='norm'" @input="onEditorInput('norm', $event)" v-html="methodologySections.norm" style="min-height: 70px; padding: 10px; border: 1px solid #ddd; border-radius: 4px; background: #fff;"></div>
                                    <div style="color:#666; font-size: 12px; margin-top: 4px;">已输入 {{ getEditorTextLen('norm') }} 字 / 上限 {{ getEditorLimit('norm') }} 字</div>
                                </div>

                                <div style="margin-top: 14px; display:flex; gap: 12px; flex-wrap: wrap;">
                                    <div>
                                        <div style="font-size: 12px; color:#666; margin-bottom: 6px;">大挑项目技术路线图/研究框架图（必传）</div>
                                        <input type="file" accept="image/*" @change="(e) => handleProcessUpload(e, 'methodology', 'route_map')" />
                                    </div>
                                    <div>
                                        <div style="font-size: 12px; color:#666; margin-bottom: 6px;">大挑科技发明制作类实物/模型照片（社科/自然科学类可传调研现场/数据图）</div>
                                        <input type="file" accept="image/*" @change="(e) => handleProcessUpload(e, 'methodology', 'photo')" />
                                    </div>
                                    <div>
                                        <div style="font-size: 12px; color:#666; margin-bottom: 6px;">大挑参赛脱敏附件（仅限脱敏后的论文/调查报告/路演PPT，严禁包含敏感信息）</div>
                                        <input type="file" accept=".pdf,.ppt,.pptx,.doc,.docx,.zip,.rar" @change="(e) => handleProcessUpload(e, 'methodology', 'attachment')" />
                                    </div>
                                    <div>
                                        <div style="font-size: 12px; color:#666; margin-bottom: 6px;">规范性材料（可选）：大挑申报书/查新报告/鉴定证书（脱敏后上传）</div>
                                        <input type="file" accept=".pdf,.ppt,.pptx,.doc,.docx,.zip,.rar" @change="(e) => handleProcessUpload(e, 'methodology', 'compliance_material')" />
                                    </div>
                                </div>

                                <div style="margin-top: 12px;">
                                    <el-button type="primary" @click="submitMethodologyRich()" :loading="submittingMethodology" :disabled="!canSubmitDachuangExperience()">提交方法论总结</el-button>
                                    <span v-if="currentProject.extra_info?.methodology_submitted_at" style="margin-left: 10px; color:#666;">已提交：{{ currentProject.extra_info.methodology_submitted_at }}</span>
                                </div>
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

        <el-dialog v-model="showUpgradeDialog" title="申请升级" width="520px">
            <el-form :model="upgradeForm" label-width="90px">
                <el-form-item label="升级目标" required>
                    <el-select v-model="upgradeForm.to_level" style="width: 100%">
                        <el-option label="省级" value="provincial"></el-option>
                        <el-option label="国家级" value="national"></el-option>
                    </el-select>
                </el-form-item>
                <el-form-item label="申请说明">
                    <el-input v-model="upgradeForm.reason" type="textarea" :rows="4" placeholder="可选"></el-input>
                </el-form-item>
            </el-form>
            <template #footer>
                <el-button @click="showUpgradeDialog = false">取消</el-button>
                <el-button type="primary" @click="submitUpgradeRequest" :loading="submitting">提交</el-button>
            </template>
        </el-dialog>

        <el-dialog v-model="showLinkDachuangDialog" title="关联已有大创项目" width="700px">
            <div style="margin-bottom: 10px; color: #666;">
                检测到你已有立项的大创项目，可选择关联以复用成果数据（可跳过）。
            </div>
            <el-table :data="dachuangCandidates" border size="small" @row-click="row => dachuangLinkSelected = row.id">
                <el-table-column width="60" label="">
                    <template #default="scope">
                        <el-tag v-if="dachuangLinkSelected === scope.row.id" type="success" size="small">已选</el-tag>
                    </template>
                </el-table-column>
                <el-table-column prop="title" label="项目名称"></el-table-column>
                <el-table-column prop="level" label="级别" width="100">
                    <template #default="scope">{{ getProjectLevelText(scope.row.level) }}</template>
                </el-table-column>
                <el-table-column prop="status" label="状态" width="120"></el-table-column>
            </el-table>
            <template #footer>
                <el-button @click="skipLinkDachuang">跳过</el-button>
                <el-button type="primary" @click="confirmLinkDachuang">确认关联</el-button>
            </template>
        </el-dialog>

        <el-dialog v-model="showAwardDialog" title="获奖记录" width="650px">
            <el-form :model="awardForm" label-width="90px">
                <el-form-item label="关联项目" required>
                    <el-select v-model="awardForm.project_id" filterable style="width: 100%">
                        <el-option v-for="p in projects" :key="p.id" :label="p.title" :value="p.id"></el-option>
                    </el-select>
                </el-form-item>
                <el-row :gutter="20">
                    <el-col :span="12">
                        <el-form-item label="阶段" required>
                            <el-select v-model="awardForm.stage" style="width: 100%">
                                <el-option label="省赛" value="provincial"></el-option>
                                <el-option label="国赛" value="national"></el-option>
                            </el-select>
                        </el-form-item>
                    </el-col>
                    <el-col :span="12">
                        <el-form-item label="等级" required>
                            <el-select v-model="awardForm.award_level" style="width: 100%" placeholder="请选择或输入" filterable allow-create clearable>
                                <el-option v-for="opt in getDynamicAwardOptions(getAwardDialogProject())" :key="opt" :label="getAwardLevelLabel(opt) || opt" :value="opt"></el-option>
                                <el-option label="无" value="none"></el-option>
                            </el-select>
                        </el-form-item>
                    </el-col>
                </el-row>
                <el-form-item label="奖项名称">
                    <el-input v-model="awardForm.award_name"></el-input>
                </el-form-item>
                <el-row :gutter="20">
                    <el-col :span="12">
                        <el-form-item label="获奖时间">
                            <el-input v-model="awardForm.award_time" placeholder="例如：2025-10"></el-input>
                        </el-form-item>
                    </el-col>
                    <el-col :span="12">
                        <el-form-item label="颁奖单位">
                            <el-input v-model="awardForm.issuer"></el-input>
                        </el-form-item>
                    </el-col>
                </el-row>
            </el-form>
            <template #footer>
                <el-button @click="showAwardDialog = false">取消</el-button>
                <el-button type="primary" @click="submitAward">保存</el-button>
            </template>
        </el-dialog>

        <!-- 评审弹窗 -->
        <!-- 评审任务分配弹窗 -->
        <el-dialog v-model="showAssignDialog" title="分配评委" width="500px">
            <el-form label-width="80px">
                <el-form-item label="选择评委">
                    <el-select v-model="assignForm.judge_ids" multiple placeholder="请选择评委" style="width: 100%">
                        <el-option v-for="judge in availableJudges" :key="judge.id" :label="judge.real_name + ' (' + judge.department + ')'" :value="judge.id"></el-option>
                    </el-select>
                </el-form-item>
                <el-form-item label="评审级别">
                    <el-radio-group v-model="assignForm.review_level">
                        <el-radio label="college">学院赛</el-radio>
                        <el-radio label="school" v-if="user?.role === 'school_approver' || user?.role === 'system_admin'">校赛</el-radio>
                    </el-radio-group>
                </el-form-item>
            </el-form>
            <template #footer>
                <el-button @click="showAssignDialog = false">取消</el-button>
                <el-button type="primary" @click="submitAssignReviewers" :loading="submitting">确认分配</el-button>
            </template>
        </el-dialog>

        <!-- 任务评审弹窗 (评委端) -->
        <el-dialog v-model="showTaskReviewDialog" title="评审项目" width="600px">
            <el-form v-if="currentTask" label-width="120px">
                <div style="margin-bottom: 20px; padding: 10px; background: #f5f7fa; border-radius: 4px;">
                    <strong>项目名称：</strong> {{ currentTask.project_title }}<br/>
                    <el-button type="primary" link @click="viewDetails(currentTask.project_id)">点击查看项目详情</el-button>
                </div>

                <template v-if="currentTask.project_type === 'challenge_cup' || currentTask.project_type === 'innovation'">
                    <el-form-item label="科学性(0-30)">
                        <el-input-number v-model="taskReviewForm.criteria_scores.scientific" :min="0" :max="30"></el-input-number>
                    </el-form-item>
                    <el-form-item label="先进性(0-30)">
                        <el-input-number v-model="taskReviewForm.criteria_scores.advanced" :min="0" :max="30"></el-input-number>
                    </el-form-item>
                    <el-form-item label="应用价值(0-20)">
                        <el-input-number v-model="taskReviewForm.criteria_scores.practical" :min="0" :max="20"></el-input-number>
                    </el-form-item>
                    <el-form-item label="规范性(0-20)">
                        <el-input-number v-model="taskReviewForm.criteria_scores.normative" :min="0" :max="20"></el-input-number>
                    </el-form-item>
                    <div style="text-align: right; color: #666; margin-bottom: 15px; font-size: 14px;">
                        自动计算总分：<strong>{{ (taskReviewForm.criteria_scores.scientific || 0) + (taskReviewForm.criteria_scores.advanced || 0) + (taskReviewForm.criteria_scores.practical || 0) + (taskReviewForm.criteria_scores.normative || 0) }}</strong>
                    </div>
                </template>
                <template v-else>
                    <el-form-item label="总评分(0-100)">
                        <el-input-number v-model="taskReviewForm.criteria_scores.total" :min="0" :max="100"></el-input-number>
                    </el-form-item>
                </template>

                <el-form-item label="评审意见">
                    <el-input v-model="taskReviewForm.comments" type="textarea" :rows="4" placeholder="请输入评审意见..."></el-input>
                </el-form-item>

                <el-form-item label="推荐结论">
                    <el-radio-group v-model="taskReviewForm.is_recommended">
                        <el-radio :label="true">推荐</el-radio>
                        <el-radio :label="false">不推荐</el-radio>
                    </el-radio-group>
                </el-form-item>

                <div style="margin: 10px 0; padding: 12px; background: #fff7e6; border: 1px solid #ffd591; border-radius: 4px;">
                    <el-checkbox v-model="taskReviewForm.declaration">
                        系统已自动检测利益关系，本人确认无其他未声明的利益冲突
                    </el-checkbox>
                </div>
            </el-form>
            <template #footer>
                <el-button @click="showTaskReviewDialog = false">取消</el-button>
                <el-button type="warning" @click="submitTaskReview('draft')" :loading="submitting" v-if="currentTask?.status !== 'completed'">暂存</el-button>
                <el-button type="primary" @click="submitTaskReview('completed')" :loading="submitting" v-if="currentTask?.status !== 'completed'">提交评审 (不可修改)</el-button>
            </template>
        </el-dialog>

        <el-dialog v-model="showQuickTestDialog" title="测试账号(快速验证)" width="650px">
            <el-alert title="这些账号为测试用途，默认密码为 Test123456" type="warning" :closable="false" class="mb-3"></el-alert>
            <el-table :data="quickTestAccounts" border style="width: 100%">
                <el-table-column prop="role" label="用途" width="160"></el-table-column>
                <el-table-column prop="username" label="用户名" width="220"></el-table-column>
                <el-table-column prop="college" label="学院/分组" min-width="160"></el-table-column>
                <el-table-column label="操作" width="120" fixed="right">
                    <template #default="scope">
                        <el-button size="small" @click="copyText(scope.row.username)">复制账号</el-button>
                    </template>
                </el-table-column>
            </el-table>
            <template #footer>
                <el-button @click="showQuickTestDialog = false">关闭</el-button>
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
            <el-form :model="compForm" label-width="120px">
                <el-form-item v-if="!isEditingComp" label="快速模板">
                    <div class="template-selection-container" style="width: 100%; border: 1px solid #dcdfe6; padding: 15px; border-radius: 4px;">
                        <!-- 创新体系 -->
                        <div class="template-group">
                            <div class="group-label" style="font-weight: bold; margin-bottom: 8px; color: #409EFF; border-left: 3px solid #409EFF; padding-left: 8px;">创新体系</div>
                            <el-radio-group v-model="selectedPreset" @change="applyPreset" style="display: flex; flex-direction: column; align-items: flex-start;">
                                <el-radio border label="da_tiao" style="margin-bottom: 8px; margin-left: 0; width: 100%;">“挑战杯”全国大学生课外学术科技作品竞赛</el-radio>
                                <el-radio border label="innovation_training" style="margin-left: 0; width: 100%;">大学生创新创业训练计划·创新训练项目</el-radio>
                            </el-radio-group>
                        </div>
                        
                        <!-- 创业体系 -->
                        <div class="template-group" style="margin-top: 15px;">
                            <div class="group-label" style="font-weight: bold; margin-bottom: 8px; color: #E6A23C; border-left: 3px solid #E6A23C; padding-left: 8px;">创业体系</div>
                            <el-radio-group v-model="selectedPreset" @change="applyPreset" style="display: flex; flex-direction: column; align-items: flex-start;">
                                <el-radio border label="internet_plus" style="margin-bottom: 8px; margin-left: 0; width: 100%;">中国国际大学生创新大赛</el-radio>
                                <el-radio border label="xiao_tiao" style="margin-bottom: 8px; margin-left: 0; width: 100%;">“挑战杯”中国大学生创业计划竞赛</el-radio>
                                <el-radio border label="dachuang_entrepreneurship_training" style="margin-bottom: 8px; margin-left: 0; width: 100%;">大学生创新创业训练计划·创业训练项目</el-radio>
                                <el-radio border label="dachuang_entrepreneurship_practice" style="margin-left: 0; width: 100%;">大学生创新创业训练计划·创业实践项目</el-radio>
                            </el-radio-group>
                        </div>

                        <!-- 三创赛体系 -->
                        <div class="template-group" style="margin-top: 15px;">
                            <div class="group-label" style="font-weight: bold; margin-bottom: 8px; color: #67C23A; border-left: 3px solid #67C23A; padding-left: 8px;">三创赛体系</div>
                            <el-radio-group v-model="selectedPreset" @change="applyPreset" style="display: flex; flex-direction: column; align-items: flex-start;">
                                <el-radio border label="sanchuang_regular" style="margin-bottom: 8px; margin-left: 0; width: 100%;">全国大学生电子商务“创新、创意及创业”挑战赛·常规赛</el-radio>
                                <el-radio border label="sanchuang_practical" style="margin-left: 0; width: 100%;">全国大学生电子商务“创新、创意及创业”挑战赛·实战赛</el-radio>
                            </el-radio-group>
                        </div>
                    </div>
                    <div style="font-size: 12px; color: #999; margin-top: 5px;">选择模板可自动填充表单配置和主办/承办单位等信息，您仍可手动修改。</div>
                </el-form-item>
                <el-divider v-if="!isEditingComp"></el-divider>

                <el-form-item label="批次名称" required>
                    <el-input v-model="compForm.title" placeholder="例如：2025年大学生创新创业训练计划"></el-input>
                </el-form-item>

                <el-form-item label="模板预设">
                    <el-select v-model="selectedPreset" placeholder="请选择预设模板" style="width: 100%" @change="applyPreset">
                        <el-option v-for="p in presetTemplates" :key="p.value" :label="p.label" :value="p.value"></el-option>
                    </el-select>
                </el-form-item>
                
                <el-form-item label="表单配置">
                    <el-button type="primary" @click="openFormDesigner">⚙️ 打开动态表单设计器</el-button>
                    <div style="margin-top: 5px; font-size: 12px; color: #666;">
                        当前包含 {{ compForm.form_config?.groups?.length || 0 }} 个分组，
                        {{ (compForm.form_config?.groups || []).reduce((acc, g) => acc + g.fields.length, 0) }} 个字段
                    </div>
                </el-form-item>

                <el-form-item label="所属体系">
                     <el-select v-model="compForm.system_type" placeholder="请选择体系">
                         <el-option label="创新体系" value="创新体系"></el-option>
                         <el-option label="创业体系" value="创业体系"></el-option>
                         <el-option label="三创赛体系" value="三创赛体系"></el-option>
                     </el-select>
                </el-form-item>

                <el-form-item label="赛事等级">
                     <el-select v-model="compForm.competition_level" placeholder="请选择等级">
                         <el-option label="A类" value="A类"></el-option>
                         <el-option label="B类" value="B类"></el-option>
                         <el-option label="C类" value="C类"></el-option>
                         <el-option label="D类" value="D类"></el-option>
                     </el-select>
                </el-form-item>

                <el-form-item label="国家/省级主办单位">
                    <el-input v-model="compForm.national_organizer" placeholder="例如：教育部、团中央等"></el-input>
                </el-form-item>

                <el-form-item label="学校层面承办单位">
                    <el-input v-model="compForm.school_organizer" placeholder="例如：校团委、创新创业学院等"></el-input>
                </el-form-item>

                <el-form-item label="原批次级别" v-show="false">
                     <el-select v-model="compForm.level">
                         <el-option label="校级" value="School"></el-option>
                         <el-option label="省级" value="Provincial"></el-option>
                         <el-option label="国家级" value="National"></el-option>
                     </el-select>
                </el-form-item>
                <el-form-item label="原承办单位" v-show="false">
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
                        <template v-if="systemStats.challenge_cup_stats">
                            <el-divider>大挑(挑战杯)专属统计</el-divider>
                            <p>大挑总申报数: {{ systemStats.challenge_cup_stats.total_applications }}</p>
                            <p>大挑过审/获奖率: <el-tag type="success">{{ systemStats.challenge_cup_stats.pass_rate }}</el-tag></p>
                        </template>
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
            jiebangTopicsTree: { year: 2026, groups: [] },
            jiebangTopicsLoading: false,
            jiebangCollapseActive: [],
            jiebangAdmin: {
                year: 2026,
                keyword: '',
                groupNo: '',
                enabled: '',
                rawList: [],
                list: [],
                loading: false,
                showDialog: false,
                isEdit: false,
                form: {
                    id: null,
                    year: 2026,
                    group_no: 1,
                    group_name: '',
                    topic_no: 1,
                    topic_title: '',
                    topic_desc: '',
                    enabled: 1
                }
            },
            presetTemplates: [
                {
                    "label": "“挑战杯”全国大学生课外学术科技作品竞赛",
                    "value": "da_tiao",
                    "data": {
                        "title": "“挑战杯”全国大学生课外学术科技作品竞赛",
                        "system_type": "创新体系",
                        "competition_level": "A类",
                        "national_organizer": "共青团中央、中国科协、教育部、中国社会科学院、中国工程院、全国学联、省级人民政府",
                        "school_organizer": "校团委",
                        "level": "National",
                        "template_type": "competition",
                        "form_config": {
                            "groups": [
                                {
                                    "title": "作品基础信息",
                                    "fields": [
                                        {
                                            "key": "title",
                                            "label": "作品名称",
                                            "type": "text",
                                            "required": true,
                                            "system": true,
                                            "placeholder": "不超过20个汉字"
                                        },
                                        {
                                            "key": "extra_info.category",
                                            "label": "作品类别",
                                            "type": "radio",
                                            "required": true,
                                            "options": [
                                                { "label": "自然科学类学术论文", "value": "natural_science" },
                                                { "label": "哲学社会科学类社会调查报告和学术论文", "value": "social_science" },
                                                { "label": "科技发明制作", "value": "tech_invention" }
                                            ]
                                        },
                                        {
                                            "key": "extra_info.tech_subcategory",
                                            "label": "科技发明制作细分",
                                            "type": "radio",
                                            "required": true,
                                            "show_if": { "key": "extra_info.category", "values": ["tech_invention"] },
                                            "options": [
                                                { "label": "科技发明制作A类", "value": "a" },
                                                { "label": "科技发明制作B类", "value": "b" }
                                            ]
                                        },
                                        {
                                            "key": "extra_info.subject_natural",
                                            "label": "学科领域（自然）",
                                            "type": "select",
                                            "required": true,
                                            "show_if": { "key": "extra_info.category", "values": ["natural_science", "tech_invention"] },
                                            "options": [
                                                { "label": "机械与控制", "value": "mech" },
                                                { "label": "信息技术", "value": "it" },
                                                { "label": "数理", "value": "math" },
                                                { "label": "生命科学", "value": "life" },
                                                { "label": "能源化工", "value": "energy" }
                                            ]
                                        },
                                        {
                                            "key": "extra_info.subject_social",
                                            "label": "学科领域（社科）",
                                            "type": "select",
                                            "required": true,
                                            "show_if": { "key": "extra_info.category", "values": ["social_science"] },
                                            "options": [
                                                { "label": "哲学", "value": "philosophy" },
                                                { "label": "经济", "value": "economics" },
                                                { "label": "社会", "value": "society" },
                                                { "label": "法律", "value": "law" },
                                                { "label": "教育", "value": "education" },
                                                { "label": "管理", "value": "management" }
                                            ]
                                        }
                                    ]
                                },
                                {
                                    "title": "申报者/团队信息",
                                    "fields": [
                                        {
                                            "key": "extra_info.declaration_type",
                                            "label": "申报类型",
                                            "type": "radio",
                                            "required": true,
                                            "options": [
                                                { "label": "个人项目", "value": "individual" },
                                                { "label": "集体项目", "value": "team" }
                                            ]
                                        },
                                        {
                                            "key": "leader_name",
                                            "label": "负责人姓名",
                                            "type": "text",
                                            "required": true,
                                            "system": true
                                        },
                                        {
                                            "key": "extra_info.leader_student_id",
                                            "label": "负责人学号",
                                            "type": "text",
                                            "required": true
                                        },
                                        {
                                            "key": "college",
                                            "label": "负责人所在学院",
                                            "type": "select",
                                            "required": true,
                                            "system": true
                                        },
                                        {
                                            "key": "extra_info.leader_major_grade",
                                            "label": "负责人专业年级",
                                            "type": "text",
                                            "required": true
                                        },
                                        {
                                            "key": "extra_info.leader_degree",
                                            "label": "负责人学历",
                                            "type": "select",
                                            "required": true,
                                            "options": [
                                                { "label": "本科", "value": "undergrad" },
                                                { "label": "硕士", "value": "master" },
                                                { "label": "博士", "value": "phd" }
                                            ]
                                        },
                                        {
                                            "key": "extra_info.leader_phone",
                                            "label": "联系电话",
                                            "type": "text",
                                            "required": true
                                        },
                                        {
                                            "key": "extra_info.leader_email",
                                            "label": "电子邮箱",
                                            "type": "text",
                                            "required": true
                                        },
                                        {
                                            "key": "extra_info.collaborators_individual",
                                            "label": "合作者信息（≤2人）",
                                            "type": "table",
                                            "required": true,
                                            "show_if": { "key": "extra_info.declaration_type", "values": ["individual"] },
                                            "columns": [
                                                { "label": "姓名", "key": "姓名" },
                                                { "label": "性别", "key": "性别" },
                                                { "label": "年龄", "key": "年龄" },
                                                { "label": "学历", "key": "学历" },
                                                { "label": "所在单位", "key": "所在单位", "width": 160 }
                                            ],
                                            "placeholder": "建议填JSON数组：[{\"姓名\":\"\",\"性别\":\"\",\"年龄\":\"\",\"学历\":\"\",\"所在单位\":\"\"}]"
                                        },
                                        {
                                            "key": "extra_info.collaborators_team",
                                            "label": "合作者信息（≤8-10人）",
                                            "type": "table",
                                            "required": true,
                                            "show_if": { "key": "extra_info.declaration_type", "values": ["team"] },
                                            "columns": [
                                                { "label": "姓名", "key": "姓名" },
                                                { "label": "性别", "key": "性别" },
                                                { "label": "年龄", "key": "年龄" },
                                                { "label": "学历", "key": "学历" },
                                                { "label": "所在单位", "key": "所在单位", "width": 160 }
                                            ],
                                            "placeholder": "建议填JSON数组：[{\"姓名\":\"\",\"性别\":\"\",\"年龄\":\"\",\"学历\":\"\",\"所在单位\":\"\"}]"
                                        }
                                    ]
                                },
                                {
                                    "title": "指导教师信息",
                                    "fields": [
                                        {
                                            "key": "advisor_name",
                                            "label": "指导教师姓名",
                                            "type": "text",
                                            "required": true,
                                            "system": true
                                        },
                                        {
                                            "key": "extra_info.advisor_title",
                                            "label": "指导教师职称",
                                            "type": "select",
                                            "required": true,
                                            "options": [
                                                { "label": "教授", "value": "professor" },
                                                { "label": "副教授", "value": "associate_professor" },
                                                { "label": "研究员", "value": "researcher" },
                                                { "label": "高级工程师", "value": "senior_engineer" },
                                                { "label": "其他高级职称", "value": "other_senior" }
                                            ]
                                        },
                                        {
                                            "key": "extra_info.advisor_unit",
                                            "label": "所在单位",
                                            "type": "text",
                                            "required": true
                                        },
                                        {
                                            "key": "extra_info.advisor_research",
                                            "label": "研究领域",
                                            "type": "textarea",
                                            "required": false
                                        },
                                        {
                                            "key": "extra_info.advisor_phone",
                                            "label": "联系电话",
                                            "type": "text",
                                            "required": true
                                        }
                                    ]
                                },
                                {
                                    "title": "作品核心内容（自然科学类学术论文）",
                                    "show_if": { "key": "extra_info.category", "values": ["natural_science"] },
                                    "fields": [
                                        { "key": "extra_info.ns_purpose_idea", "label": "作品撰写目的与思路", "type": "richtext", "required": true },
                                        { "key": "extra_info.ns_scientific_advantage", "label": "科学性与先进性", "type": "richtext", "required": true },
                                        { "key": "extra_info.ns_application_value", "label": "作品的实际应用价值和现实意义", "type": "richtext", "required": true },
                                        { "key": "extra_info.ns_abstract", "label": "学术论文文摘", "type": "richtext", "required": true, "placeholder": "200-300字" },
                                        { "key": "extra_info.ns_keywords", "label": "关键词", "type": "textarea", "required": true, "placeholder": "3-8个" },
                                        { "key": "extra_info.attachments.ns_full_text", "label": "论文全文", "type": "file", "required": true, "accept": ".pdf,.doc,.docx", "placeholder": "PDF格式，≤8000 字" },
                                        { "key": "extra_info.ns_references", "label": "参考文献", "type": "table", "required": true, "columns": [ { "label": "序号", "key": "序号", "width": 80 }, { "label": "文献", "key": "文献", "width": 420 } ], "placeholder": "按顺序录入参考文献" },
                                        { "key": "extra_info.attachments.plagiarism_report", "label": "查重报告", "type": "file", "required": true, "accept": ".pdf", "placeholder": "PDF格式" }
                                    ]
                                },
                                {
                                    "title": "作品核心内容（哲学社会科学类社会调查报告和学术论文）",
                                    "show_if": { "key": "extra_info.category", "values": ["social_science"] },
                                    "fields": [
                                        { "key": "extra_info.ss_purpose_idea", "label": "作品撰写目的与思路", "type": "richtext", "required": true },
                                        { "key": "extra_info.ss_scientific_advantage", "label": "科学性与先进性", "type": "richtext", "required": true },
                                        { "key": "extra_info.ss_application_value", "label": "作品的实际应用价值和现实指导意义", "type": "richtext", "required": true },
                                        { "key": "extra_info.ss_abstract", "label": "作品摘要", "type": "richtext", "required": true },
                                        {
                                            "key": "extra_info.ss_survey_methods",
                                            "label": "调查方式",
                                            "type": "checkbox",
                                            "required": true,
                                            "options": [
                                                { "label": "走访", "value": "visit" },
                                                { "label": "问卷", "value": "questionnaire" },
                                                { "label": "现场采访", "value": "interview" },
                                                { "label": "个别交谈", "value": "talk" },
                                                { "label": "亲临实践", "value": "practice" },
                                                { "label": "会议", "value": "meeting" },
                                                { "label": "书报刊物", "value": "publications" },
                                                { "label": "统计报表", "value": "statistics" },
                                                { "label": "影视资料", "value": "video" },
                                                { "label": "文件", "value": "documents" },
                                                { "label": "集体组织", "value": "organization" },
                                                { "label": "自发", "value": "spontaneous" },
                                                { "label": "其它", "value": "other" }
                                            ]
                                        },
                                        { "key": "extra_info.ss_survey_units_count", "label": "主要调查单位及调查数量", "type": "text", "required": true, "placeholder": "省/市/县/乡/村/单位数量、人次" },
                                        { "key": "extra_info.attachments.ss_full_report", "label": "调查报告全文", "type": "file", "required": true, "accept": ".pdf,.doc,.docx", "placeholder": "PDF格式，≤15000 字" }
                                    ]
                                },
                                {
                                    "title": "作品核心内容（科技发明制作）",
                                    "show_if": { "key": "extra_info.category", "values": ["tech_invention"] },
                                    "fields": [
                                        { "key": "extra_info.ti_purpose_idea", "label": "作品设计、发明的目的和基本思路", "type": "richtext", "required": true },
                                        { "key": "extra_info.ti_innovation", "label": "创新点", "type": "richtext", "required": true },
                                        { "key": "extra_info.ti_key_indicators", "label": "技术关键和主要技术指标", "type": "richtext", "required": true },
                                        { "key": "extra_info.ti_scientific_advanced", "label": "作品的科学性先进性", "type": "richtext", "required": true },
                                        {
                                            "key": "extra_info.ti_stage",
                                            "label": "作品所处阶段",
                                            "type": "radio",
                                            "required": true,
                                            "options": [
                                                { "label": "实验室阶段", "value": "lab" },
                                                { "label": "中试阶段", "value": "pilot" },
                                                { "label": "生产阶段", "value": "production" }
                                            ]
                                        },
                                        { "key": "extra_info.ti_transfer_method", "label": "技术转让方式", "type": "text", "required": false },
                                        {
                                            "key": "extra_info.ti_display_forms",
                                            "label": "作品可展示的形式",
                                            "type": "checkbox",
                                            "required": true,
                                            "options": [
                                                { "label": "实物、产品", "value": "product" },
                                                { "label": "模型", "value": "model" },
                                                { "label": "图纸", "value": "drawing" },
                                                { "label": "磁盘", "value": "disk" },
                                                { "label": "现场演示", "value": "live_demo" },
                                                { "label": "图片", "value": "images" },
                                                { "label": "录像", "value": "video" },
                                                { "label": "样品", "value": "sample" }
                                            ]
                                        },
                                        { "key": "extra_info.ti_instructions", "label": "使用说明及技术特点", "type": "richtext", "required": true },
                                        {
                                            "key": "extra_info.ti_patent_status",
                                            "label": "专利申报情况",
                                            "type": "radio",
                                            "required": false,
                                            "options": [
                                                { "label": "提出专利申报", "value": "applied" },
                                                { "label": "已获专利权批准", "value": "granted" },
                                                { "label": "未提出专利申请", "value": "none" }
                                            ]
                                        },
                                        { "key": "extra_info.ti_patent_number", "label": "专利号/申报号", "type": "text", "required": true, "show_if": { "key": "extra_info.ti_patent_status", "values": ["applied", "granted"] } },
                                        { "key": "extra_info.attachments.ti_report", "label": "研究报告", "type": "file", "required": true, "accept": ".pdf,.doc,.docx", "placeholder": "字数3000字以上，含图表、数据、原理结构图" }
                                    ]
                                },
                                {
                                    "title": "附加材料",
                                    "fields": [
                                        { "key": "extra_info.recommenders", "label": "推荐者信息", "type": "table", "required": true, "columns": [ { "label": "推荐者姓名", "key": "推荐者姓名" }, { "label": "职称", "key": "职称" }, { "label": "工作单位", "key": "工作单位", "width": 180 }, { "label": "推荐意见", "key": "推荐意见", "width": 260 } ], "placeholder": "须高级职称，且与作品同领域" },
                                        { "key": "extra_info.attachments.support_materials", "label": "支撑材料", "type": "file", "required": false, "accept": ".pdf,.jpg,.png,.zip,.rar", "placeholder": "图片、数据、原理图、照片、鉴定证书等" }
                                    ]
                                }
                            ]
                        }
                    }
                },
                {
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
                                        { "key": "title", "label": "选题名称", "type": "text", "required": true, "system": true },
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
                                        { "key": "members", "label": "团队成员", "type": "table", "required": true, "system": true, "columns": [{ "label": "学号", "key": "student_id", "width": 140 }, { "label": "姓名", "key": "name", "width": 100 }, { "label": "学院", "key": "college", "width": 150 }, { "label": "年级", "key": "grade", "width": 100 }, { "label": "专业", "key": "major", "width": 160 }, { "label": "角色", "key": "role", "width": 120 }] }
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
                },
                {
                    "label": "中国国际大学生创新大赛",
                    "value": "internet_plus",
                    "data": {
                        "title": "中国国际大学生创新大赛",
                        "system_type": "创业体系",
                        "competition_level": "A类",
                        "national_organizer": "教育部、中央统战部、中央网信办、国家发展改革委、工业和信息化部、人力资源社会保障部、农业农村部、中国科学院、中国工程院、国家知识产权局、共青团中央、省级人民政府",
                        "school_organizer": "创新创业学院",
                        "level": "National",
                        "template_type": "competition",
                        "form_config": {
                            "groups": [
                                {
                                    "title": "项目基础信息",
                                    "fields": [
                                        {
                                            "key": "title",
                                            "label": "项目名称",
                                            "type": "text",
                                            "required": true,
                                            "system": true
                                        },
                                        {
                                            "key": "extra_info.track",
                                            "label": "参赛赛道",
                                            "type": "select",
                                            "required": true,
                                            "options": [
                                                {
                                                    "label": "高教主赛道",
                                                    "value": "main"
                                                },
                                                {
                                                    "label": "红旅赛道",
                                                    "value": "red"
                                                },
                                                {
                                                    "label": "产业命题赛道",
                                                    "value": "industry"
                                                }
                                            ]
                                        },
                                        {
                                            "key": "extra_info.project_type_4new",
                                            "label": "项目类型（四新）",
                                            "type": "select",
                                            "required": true,
                                            "options": [
                                                {
                                                    "label": "新工科类",
                                                    "value": "engineering"
                                                },
                                                {
                                                    "label": "新医科类",
                                                    "value": "medical"
                                                },
                                                {
                                                    "label": "新农科类",
                                                    "value": "agriculture"
                                                },
                                                {
                                                    "label": "新文科类",
                                                    "value": "liberal_arts"
                                                }
                                            ]
                                        },
                                        {
                                            "key": "extra_info.group",
                                            "label": "参赛组别",
                                            "type": "select",
                                            "required": true,
                                            "options": [
                                                {
                                                    "label": "本科生创意组",
                                                    "value": "undergrad_idea"
                                                },
                                                {
                                                    "label": "研究生创意组",
                                                    "value": "grad_idea"
                                                },
                                                {
                                                    "label": "初创组",
                                                    "value": "startup"
                                                },
                                                {
                                                    "label": "成长组",
                                                    "value": "growth"
                                                },
                                                {
                                                    "label": "师生共创组",
                                                    "value": "teacher_student"
                                                }
                                            ]
                                        }
                                    ]
                                },
                                {
                                    "title": "核心内容",
                                    "fields": [
                                        {
                                            "key": "abstract",
                                            "label": "执行概要",
                                            "type": "richtext",
                                            "required": true,
                                            "system": true,
                                            "placeholder": "300-500字"
                                        },
                                        {
                                            "key": "extra_info.market_pain_points",
                                            "label": "市场痛点分析",
                                            "type": "richtext",
                                            "required": true
                                        },
                                        {
                                            "key": "extra_info.product_solution",
                                            "label": "产品/解决方案",
                                            "type": "richtext",
                                            "required": true
                                        },
                                        {
                                            "key": "extra_info.business_model",
                                            "label": "商业模式",
                                            "type": "richtext",
                                            "required": true
                                        },
                                        {
                                            "key": "extra_info.core_competitiveness",
                                            "label": "核心竞争力",
                                            "type": "richtext",
                                            "required": true
                                        },
                                        {
                                            "key": "extra_info.operation_status",
                                            "label": "运营现状",
                                            "type": "richtext",
                                            "required": true
                                        }
                                    ]
                                },
                                {
                                    "title": "财务与融资",
                                    "fields": [
                                        {
                                            "key": "extra_info.equity_structure",
                                            "label": "股本结构",
                                            "type": "table",
                                            "required": true
                                        },
                                        {
                                            "key": "extra_info.financing_needs",
                                            "label": "融资需求",
                                            "type": "table",
                                            "required": true
                                        },
                                        {
                                            "key": "extra_info.financial_forecast",
                                            "label": "财务预测",
                                            "type": "table",
                                            "required": true
                                        }
                                    ]
                                },
                                {
                                    "title": "团队信息",
                                    "fields": [
                                        {
                                            "key": "members",
                                            "label": "项目成员",
                                            "type": "table",
                                            "required": true,
                                            "system": true,
                                            "columns": [{ "label": "学号", "key": "student_id", "width": 140 }, { "label": "姓名", "key": "name", "width": 100 }, { "label": "学院", "key": "college", "width": 150 }, { "label": "年级", "key": "grade", "width": 100 }, { "label": "专业", "key": "major", "width": 160 }, { "label": "角色", "key": "role", "width": 120 }]
                                        },
                                        {
                                            "key": "advisor_name",
                                            "label": "指导教师",
                                            "type": "text",
                                            "required": true,
                                            "system": true
                                        }
                                    ]
                                },
                                {
                                    "title": "附件材料",
                                    "fields": [
                                        {
                                            "key": "extra_info.attachments.business_plan",
                                            "label": "商业计划书",
                                            "type": "file",
                                            "required": true,
                                            "placeholder": "PDF格式，≤20M"
                                        },
                                        {
                                            "key": "extra_info.attachments.pitch_deck",
                                            "label": "路演PPT",
                                            "type": "file",
                                            "required": true,
                                            "placeholder": "PPT/PPTX格式"
                                        },
                                        {
                                            "key": "extra_info.attachments.video",
                                            "label": "1分钟视频",
                                            "type": "file",
                                            "required": false,
                                            "placeholder": "MP4格式（省赛/国赛强制）"
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                },
                {
                    "label": "“挑战杯”中国大学生创业计划竞赛",
                    "value": "xiao_tiao",
                    "data": {
                        "title": "“挑战杯”中国大学生创业计划竞赛",
                        "system_type": "创业体系",
                        "competition_level": "A类",
                        "national_organizer": "共青团中央、教育部、人力资源社会保障部、中国科协、全国学联、省级人民政府",
                        "school_organizer": "校团委（创新创业学院协同）",
                        "level": "National",
                        "template_type": "competition",
                        "form_config": {
                            "groups": [
                                {
                                    "title": "项目基础信息",
                                    "fields": [
                                        {
                                            "key": "title",
                                            "label": "项目名称",
                                            "type": "text",
                                            "required": true,
                                            "system": true
                                        },
                                        {
                                            "key": "extra_info.group",
                                            "label": "参赛组别",
                                            "type": "select",
                                            "required": true,
                                            "options": [
                                                {
                                                    "label": "科技创新和未来产业",
                                                    "value": "tech_innovation"
                                                },
                                                {
                                                    "label": "乡村振兴和农业农村现代化",
                                                    "value": "rural_revitalization"
                                                },
                                                {
                                                    "label": "社会治理和公共服务",
                                                    "value": "social_governance"
                                                },
                                                {
                                                    "label": "生态环保和可持续发展",
                                                    "value": "eco_sustainability"
                                                },
                                                {
                                                    "label": "文化创意和区域合作",
                                                    "value": "cultural_creative"
                                                }
                                            ]
                                        }
                                    ]
                                },
                                {
                                    "title": "核心内容",
                                    "fields": [
                                        {
                                            "key": "abstract",
                                            "label": "执行概要",
                                            "type": "richtext",
                                            "required": true,
                                            "system": true
                                        },
                                        {
                                            "key": "extra_info.market_analysis",
                                            "label": "市场分析",
                                            "type": "richtext",
                                            "required": true
                                        },
                                        {
                                            "key": "extra_info.product_service",
                                            "label": "产品/服务",
                                            "type": "richtext",
                                            "required": true
                                        },
                                        {
                                            "key": "extra_info.business_model",
                                            "label": "商业模式",
                                            "type": "richtext",
                                            "required": true
                                        },
                                        {
                                            "key": "extra_info.financial_analysis",
                                            "label": "财务分析",
                                            "type": "richtext",
                                            "required": true
                                        }
                                    ]
                                },
                                {
                                    "title": "团队信息",
                                    "fields": [
                                        {
                                            "key": "members",
                                            "label": "项目成员",
                                            "type": "table",
                                            "required": true,
                                            "system": true,
                                            "columns": [{ "label": "学号", "key": "student_id", "width": 140 }, { "label": "姓名", "key": "name", "width": 100 }, { "label": "学院", "key": "college", "width": 150 }, { "label": "年级", "key": "grade", "width": 100 }, { "label": "专业", "key": "major", "width": 160 }, { "label": "角色", "key": "role", "width": 120 }]
                                        },
                                        {
                                            "key": "advisor_name",
                                            "label": "指导教师",
                                            "type": "text",
                                            "required": true,
                                            "system": true
                                        }
                                    ]
                                },
                                {
                                    "title": "附件材料",
                                    "fields": [
                                        {
                                            "key": "extra_info.attachments.business_plan",
                                            "label": "商业计划书",
                                            "type": "file",
                                            "required": true,
                                            "placeholder": "PDF格式"
                                        },
                                        {
                                            "key": "extra_info.attachments.pitch_deck",
                                            "label": "路演PPT",
                                            "type": "file",
                                            "required": true,
                                            "placeholder": "PPT/PPTX格式"
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                },
                {
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
                                        { "key": "title", "label": "选题名称", "type": "text", "required": true, "system": true },
                                        { "key": "project_type", "label": "项目类型", "type": "select", "required": true, "system": true, "options": [{ "label": "创业训练", "value": "entrepreneurship_training" }] },
                                        { "key": "extra_info.duration", "label": "研究周期", "type": "select", "required": true, "options": [{ "label": "1年", "value": "1" }, { "label": "2年", "value": "2" }] },
                                        { "key": "college", "label": "所属学院", "type": "select", "required": true, "system": true, "options": [] }
                                    ]
                                },
                                {
                                    "title": "指导教师信息",
                                    "fields": []
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
                                        { "key": "members", "label": "团队成员", "type": "table", "required": true, "system": true, "columns": [{ "label": "学号", "key": "student_id", "width": 140 }, { "label": "姓名", "key": "name", "width": 100 }, { "label": "学院", "key": "college", "width": 150 }, { "label": "年级", "key": "grade", "width": 100 }, { "label": "专业", "key": "major", "width": 160 }, { "label": "角色", "key": "role", "width": 120 }] }
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
                },
                {
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
                                        { "key": "title", "label": "选题名称", "type": "text", "required": true, "system": true },
                                        { "key": "project_type", "label": "项目类型", "type": "select", "required": true, "system": true, "options": [{ "label": "创业实践", "value": "entrepreneurship_practice" }] },
                                        { "key": "extra_info.duration", "label": "研究周期", "type": "select", "required": true, "options": [{ "label": "1年", "value": "1" }, { "label": "2年", "value": "2" }] },
                                        { "key": "college", "label": "所属学院", "type": "select", "required": true, "system": true, "options": [] }
                                    ]
                                },
                                {
                                    "title": "指导教师信息",
                                    "fields": []
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
                                        { "key": "members", "label": "团队成员", "type": "table", "required": true, "system": true, "columns": [{ "label": "学号", "key": "student_id", "width": 140 }, { "label": "姓名", "key": "name", "width": 100 }, { "label": "学院", "key": "college", "width": 150 }, { "label": "年级", "key": "grade", "width": 100 }, { "label": "专业", "key": "major", "width": 160 }, { "label": "角色", "key": "role", "width": 120 }] },
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
                },
                {
                    "label": "全国大学生电子商务“创新、创意及创业”挑战赛·常规赛",
                    "value": "sanchuang_regular",
                    "data": {
                        "title": "全国大学生电子商务“创新、创意及创业”挑战赛·常规赛",
                        "system_type": "三创赛体系",
                        "competition_level": "A类",
                        "national_organizer": "全国电子商务产教融合创新联盟、西安交通大学",
                        "school_organizer": "创新创业学院",
                        "level": "National",
                        "template_type": "competition",
                        "form_config": {
                            "groups": [
                                {
                                    "title": "项目基础信息",
                                    "fields": [
                                        {
                                            "key": "title",
                                            "label": "项目名称",
                                            "type": "text",
                                            "required": true,
                                            "system": true
                                        },
                                        {
                                            "key": "extra_info.theme",
                                            "label": "参赛主题",
                                            "type": "select",
                                            "required": true,
                                            "options": [
                                                {
                                                    "label": "三农电商",
                                                    "value": "agriculture"
                                                },
                                                {
                                                    "label": "工业电商",
                                                    "value": "industry"
                                                },
                                                {
                                                    "label": "跨境电商",
                                                    "value": "cross_border"
                                                },
                                                {
                                                    "label": "电商物流",
                                                    "value": "logistics"
                                                },
                                                {
                                                    "label": "互联网金融",
                                                    "value": "finance"
                                                },
                                                {
                                                    "label": "移动电商",
                                                    "value": "mobile"
                                                },
                                                {
                                                    "label": "旅游电商",
                                                    "value": "tourism"
                                                },
                                                {
                                                    "label": "校园电商",
                                                    "value": "campus"
                                                },
                                                {
                                                    "label": "其他电商",
                                                    "value": "other"
                                                }
                                            ]
                                        }
                                    ]
                                },
                                {
                                    "title": "核心内容",
                                    "fields": [
                                        {
                                            "key": "extra_info.innovation",
                                            "label": "项目创新点",
                                            "type": "richtext",
                                            "required": true
                                        },
                                        {
                                            "key": "extra_info.creativity",
                                            "label": "项目创意点",
                                            "type": "richtext",
                                            "required": true
                                        },
                                        {
                                            "key": "extra_info.feasibility",
                                            "label": "项目可行性分析",
                                            "type": "richtext",
                                            "required": true
                                        },
                                        {
                                            "key": "extra_info.business_model",
                                            "label": "商业模式设计",
                                            "type": "richtext",
                                            "required": true
                                        }
                                    ]
                                },
                                {
                                    "title": "团队信息",
                                    "fields": [
                                        {
                                            "key": "members",
                                            "label": "团队成员",
                                            "type": "table",
                                            "required": true,
                                            "system": true,
                                            "columns": [{ "label": "学号", "key": "student_id", "width": 140 }, { "label": "姓名", "key": "name", "width": 100 }, { "label": "学院", "key": "college", "width": 150 }, { "label": "年级", "key": "grade", "width": 100 }, { "label": "专业", "key": "major", "width": 160 }, { "label": "角色", "key": "role", "width": 120 }]
                                        },
                                        {
                                            "key": "advisor_name",
                                            "label": "指导教师",
                                            "type": "text",
                                            "required": true,
                                            "system": true
                                        }
                                    ]
                                },
                                {
                                    "title": "附件材料",
                                    "fields": [
                                        {
                                            "key": "extra_info.attachments.business_plan",
                                            "label": "商业计划书",
                                            "type": "file",
                                            "required": true,
                                            "placeholder": "PDF格式"
                                        },
                                        {
                                            "key": "extra_info.attachments.pitch_deck",
                                            "label": "路演PPT",
                                            "type": "file",
                                            "required": true,
                                            "placeholder": "PPT/PPTX格式"
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                },
                {
                    "label": "全国大学生电子商务“创新、创意及创业”挑战赛·实战赛",
                    "value": "sanchuang_practical",
                    "data": {
                        "title": "全国大学生电子商务“创新、创意及创业”挑战赛·实战赛",
                        "system_type": "三创赛体系",
                        "competition_level": "A类",
                        "national_organizer": "全国电子商务产教融合创新联盟、西安交通大学",
                        "school_organizer": "相关学院",
                        "level": "National",
                        "template_type": "competition",
                        "form_config": {
                            "groups": [
                                {
                                    "title": "项目基础信息",
                                    "fields": [
                                        {
                                            "key": "title",
                                            "label": "项目名称",
                                            "type": "text",
                                            "required": true,
                                            "system": true
                                        },
                                        {
                                            "key": "extra_info.track",
                                            "label": "实战赛赛道",
                                            "type": "select",
                                            "required": true,
                                            "options": [
                                                {
                                                    "label": "跨境电商",
                                                    "value": "cross_border"
                                                },
                                                {
                                                    "label": "乡村振兴",
                                                    "value": "rural_revitalization"
                                                },
                                                {
                                                    "label": "产学用(BUC)",
                                                    "value": "buc"
                                                },
                                                {
                                                    "label": "大数据",
                                                    "value": "big_data"
                                                },
                                                {
                                                    "label": "直播电商",
                                                    "value": "live_streaming"
                                                },
                                                {
                                                    "label": "文旅电商",
                                                    "value": "tourism"
                                                },
                                                {
                                                    "label": "AI电商",
                                                    "value": "ai"
                                                },
                                                {
                                                    "label": "大健康电商",
                                                    "value": "health"
                                                },
                                                {
                                                    "label": "美妆",
                                                    "value": "beauty"
                                                }
                                            ]
                                        }
                                    ]
                                },
                                {
                                    "title": "核心内容",
                                    "fields": [
                                        {
                                            "key": "abstract",
                                            "label": "项目简介",
                                            "type": "richtext",
                                            "required": true,
                                            "system": true
                                        },
                                        {
                                            "key": "extra_info.operation_strategy",
                                            "label": "运营策略",
                                            "type": "richtext",
                                            "required": true
                                        },
                                        {
                                            "key": "extra_info.channels",
                                            "label": "运营平台/渠道",
                                            "type": "textarea",
                                            "required": true
                                        }
                                    ]
                                },
                                {
                                    "title": "团队信息",
                                    "fields": [
                                        {
                                            "key": "members",
                                            "label": "团队成员",
                                            "type": "table",
                                            "required": true,
                                            "system": true,
                                            "columns": [{ "label": "学号", "key": "student_id", "width": 140 }, { "label": "姓名", "key": "name", "width": 100 }, { "label": "学院", "key": "college", "width": 150 }, { "label": "年级", "key": "grade", "width": 100 }, { "label": "专业", "key": "major", "width": 160 }, { "label": "角色", "key": "role", "width": 120 }]
                                        },
                                        {
                                            "key": "advisor_name",
                                            "label": "指导教师",
                                            "type": "text",
                                            "required": true,
                                            "system": true
                                        }
                                    ]
                                },
                                {
                                    "title": "运营数据",
                                    "fields": [
                                        {
                                            "key": "extra_info.attachments.operation_data",
                                            "label": "运营数据证明",
                                            "type": "file",
                                            "required": true,
                                            "placeholder": "销售额截图、后台数据等"
                                        },
                                        {
                                            "key": "extra_info.attachments.live_record",
                                            "label": "直播/运营记录",
                                            "type": "file",
                                            "required": false,
                                            "placeholder": "视频、截图"
                                        }
                                    ]
                                },
                                {
                                    "title": "附件材料",
                                    "fields": [
                                        {
                                            "key": "extra_info.attachments.consent_form",
                                            "label": "实战赛知情书",
                                            "type": "file",
                                            "required": true,
                                            "placeholder": "需签字"
                                        },
                                        {
                                            "key": "extra_info.attachments.business_plan",
                                            "label": "商业计划书",
                                            "type": "file",
                                            "required": false,
                                            "placeholder": "PDF格式"
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                }
                ,
                {
                    "label": "2026大创创新训练项目（中南民大）",
                    "value": "cnmu_2026_dachuang_innovation",
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
                                        { "key": "members", "label": "团队成员", "type": "table", "required": true, "system": true, "columns": [{ "label": "学号", "key": "student_id", "width": 140 }, { "label": "姓名", "key": "name", "width": 100 }, { "label": "学院", "key": "college", "width": 150 }, { "label": "年级", "key": "grade", "width": 100 }, { "label": "专业", "key": "major", "width": 160 }, { "label": "角色", "key": "role", "width": 120 }] }
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
                }
                ,
                {
                    "label": "2026大创创业训练项目（中南民大）",
                    "value": "cnmu_2026_dachuang_entrepreneurship_training",
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
                                    "title": "指导教师信息",
                                    "fields": []
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
                                        { "key": "members", "label": "团队成员", "type": "table", "required": true, "system": true, "columns": [{ "label": "学号", "key": "student_id", "width": 140 }, { "label": "姓名", "key": "name", "width": 100 }, { "label": "学院", "key": "college", "width": 150 }, { "label": "年级", "key": "grade", "width": 100 }, { "label": "专业", "key": "major", "width": 160 }, { "label": "角色", "key": "role", "width": 120 }] }
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
                }
                ,
                {
                    "label": "2026大创创业实践项目（中南民大）",
                    "value": "cnmu_2026_dachuang_entrepreneurship_practice",
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
                                    "title": "指导教师信息",
                                    "fields": []
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
                                        { "key": "members", "label": "团队成员", "type": "table", "required": true, "system": true, "columns": [{ "label": "学号", "key": "student_id", "width": 140 }, { "label": "姓名", "key": "name", "width": 100 }, { "label": "学院", "key": "college", "width": 150 }, { "label": "年级", "key": "grade", "width": 100 }, { "label": "专业", "key": "major", "width": 160 }, { "label": "角色", "key": "role", "width": 120 }] },
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
                }
            ],
            compForm: { 
                title: '', level: 'School', organizer: '', registration_start: '', registration_end: '', status: 'active', 
                system_type: '', competition_level: '', national_organizer: '', school_organizer: '',
                template_type: 'training',
                form_config: {
                    groups: []
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
            createForm: { title: '', project_type: 'innovation', members: [], linked_project_id: null },
            isEditing: false,
            currentEditingId: null,
            
            // Detail / Audit
            showDetailDialog: false,
            detailActiveTab: 'basic',
            currentProject: null,
            upgradeRequests: [],
            upgradeRequestsLoading: false,
            showUpgradeDialog: false,
            upgradeForm: { project_id: null, to_level: 'provincial', reason: '' },
            adminReviewSaving: false,
            adminReviewForm: {
                review_stage: '',
                college_review_result: 'pending',
                school_review_result: 'pending',
                provincial_award_level: 'none',
                national_award_level: 'none',
                research_admin_opinion: '',
                department_head_opinion: ''
            },
            pnResultSaving: false,
            pnResultForm: {
                provincial_status: '',
                provincial_award_level: 'none',
                provincial_certificate_no: '',
                provincial_advance_national: false,
                provincial_review_comment: '',
                national_status: '',
                national_award_level: 'none',
                national_certificate_no: '',
                national_review_comment: ''
            },
            projectAwards: [],
            projectAwardsLoading: false,
            showAwardDialog: false,
            awardForm: { id: null, project_id: null, stage: 'provincial', award_level: 'none', award_name: '', award_time: '', issuer: '' },
            awardAuto: { name: '', time: '', issuer: '' },
            awardsRecords: [],
            awardsRecordsLoading: false,
            isAuditing: false,
            auditAction: '',
            auditFeedback: '',
            auditLevel: '', // New
            auditGrade: '', // New
            fileAuditFeedback: '',
            collegeRecSaving: false,
            collegeRecForm: { passed: true, feedback: '', defense_score: null, recommend_rank: null, is_key_support: false },

            showLinkDachuangDialog: false,
            dachuangCandidates: [],
            dachuangLinkSelected: null,
            
            // Create User
            showCreateUserDialog: false,
            createUserForm: {},
            
            // Edit User
            showEditUserDialog: false,
            editUserForm: {},
            
            colleges: CNMU_COLLEGES.slice(),
            CNMU_GRADE_OPTIONS: CNMU_GRADE_OPTIONS,
            departments: [],
            permissionMode: 'mixed',
            permissionModeDraft: 'mixed',
            degrees: ['大学专科', '大学本科', '硕士研究生', '博士研究生'],

            // Review
            showReviewDialog: false,
            reviewForm: { score: 80, comment: '' },
            
            // Task Review (New)
            myReviewTasks: [],
            loadingReviews: false,
            showTaskReviewDialog: false,
            currentTask: null,
            taskReviewForm: {
                criteria_scores: {},
                score_reasons: {},
                comments: '',
                is_recommended: false,
                declaration: false
            },
            
            // Advisor Review
            advisorPendingProjects: [],
            showAdvisorReviewDialog: false,
            currentAdvisorProject: null,
            advisorReviewForm: {
                status: 'pass',
                opinion: ''
            },
            submittingAdvisorReview: false,
            
            // Assign Reviewers
            showAssignDialog: false,
            assignForm: { judge_ids: [], review_level: 'college' },
            availableJudges: [],
            calculatingRank: false,

            showQuickTestDialog: false,
            bootstrappingReviews: false,
            quickTestAccounts: [
                { role: '学院管理员', username: 'test_college_admin_cs', college: '计算机学院' },
                { role: '学校管理员', username: 'test_school_admin', college: '校级' },
                { role: '院赛评委(组长)', username: 'test_cc_college_leader', college: '计算机学院' },
                { role: '院赛评委', username: 'test_cc_college_judge1', college: '计算机学院' },
                { role: '院赛评委', username: 'test_cc_college_judge2', college: '计算机学院' },
                { role: '校赛社科(组长)', username: 'test_cc_school_social_leader', college: '社科组' },
                { role: '校赛社科', username: 'test_cc_school_social_judge1', college: '社科组' },
                { role: '校赛社科', username: 'test_cc_school_social_judge2', college: '社科组' },
                { role: '校赛理工(组长)', username: 'test_cc_school_science_leader', college: '理工组' },
                { role: '校赛理工', username: 'test_cc_school_science_judge1', college: '理工组' },
                { role: '校赛理工', username: 'test_cc_school_science_judge2', college: '理工组' }
            ],
            
            submitting: false,
            submittingProcess: false,
            processFiles: { 
                midterm: { report: null, achievement: null }, 
                conclusion: { report: null, achievement: null },
                methodology: { route_map: null, photo: null, attachment: null, compliance_material: null }
            },
            submittingMethodology: false,
            methodologySummary: '',
            methodologySections: { bg: '', process: '', innovation: '', effect: '', norm: '' },
            activeEditorKey: '',
            projectProcess: null,
            projectProcessLoading: false,
            projectProcessSaving: {}, // 修改为对象，记录各节点保存状态
            
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
            legacyCategory: 'all',
            inspirationOptions: [],
            inspirationLoading: false,
            
            // Admin: 手动收录经验库（创新类自动生成；创业类填写公开内容）
            legacyAdminForm: {
                original_project_id: null,
                category: 'innovation',
                industry_field: '',
                team_experience: '',
                pitfalls: '',
                business_model_overview: ''
            },
            adminLegacySaving: false
        }
    },
    computed: {
        canManageUsers() {
            const role = this.user?.role;
            if (!role) return false;
            if (this.permissionMode === 'strict') return role === 'system_admin';
            return ['system_admin', 'project_admin', 'college_approver'].includes(role);
        },
        canManageSystem() {
            return this.user?.role && ['system_admin', 'project_admin'].includes(this.user.role);
        },
        canManageCompetitions() {
            return this.user?.role && ['system_admin', 'project_admin'].includes(this.user.role);
        },
        canManageJiebangTopics() {
            return this.user?.role && ['system_admin', 'project_admin'].includes(this.user.role);
        },
        showJiebangTopicPanel() {
            return this.user?.role === 'student' && this.createForm?.project_type === 'innovation' && this.createForm?.template_type === 'training';
        },
        canManageAwards() {
            return this.user?.role && ['system_admin', 'project_admin', 'school_approver'].includes(this.user.role);
        },
        createDialogTitle() {
            const override = this.createForm?.form_config?.dialog_title;
            if (override) return override;

            const compId = this.createForm?.competition_id;
            const comp = compId ? (this.competitions || []).find(c => String(c.id) === String(compId)) : null;
            const baseTitle = (comp && comp.title) ? comp.title : ((this.createForm?.title || '').split(' - ')[0] || '');

            if (!baseTitle) return '项目申报';
            if (baseTitle.includes('挑战杯') && baseTitle.includes('课外学术科技作品竞赛')) return '挑战杯大挑项目申报';
            if (baseTitle.includes('挑战杯') && baseTitle.includes('创业计划')) return '挑战杯小挑项目申报';
            return `${baseTitle}项目申报`;
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
        },
        advisorTitleOptions() {
            return ['教授', '副教授', '讲师', '助教', '研究员', '副研究员', '高级工程师', '工程师', '其他'];
        },
        advisorOrgOptions() {
            const base = []
                .concat(Array.isArray(CNMU_COLLEGES) ? CNMU_COLLEGES : [])
                .concat(Array.isArray(ORG_DEPARTMENTS) ? ORG_DEPARTMENTS : []);
            const out = [];
            for (const v of base) {
                if (!v) continue;
                if (v === '创新创业学院') continue;
                if (v === '信息化建设管理处') continue;
                if (out.includes(v)) continue;
                out.push(v);
            }
            return out;
        },
        shouldShowAdvisorGuidanceType() {
            const ptype = String(this.createForm?.project_type || '');
            if (ptype === 'entrepreneurship_practice' || ptype === 'entrepreneurship_training') return true;
            const title = this.getCompetitionTitleById(this.createForm?.competition_id);
            if (!title) return false;
            return title.includes('中国国际大学生创新大赛') || title.includes('国创') || title.includes('三创');
        },
        maxCreateStep() {
            return this.createForm?.template_type === 'startup' ? 2 : 0;
        }
    },
    async mounted() {
        this.fetchProjects();
        this.fetchAnnouncements(); // 获取公告
        this.fetchCompetitions(); // 获取赛事
        await this.fetchJiebangTopicsTree();
        await this.fetchMyReviewTasks(); // 获取评审任务
        if (this.user?.role === 'judge') {
            this.activeTab = 'my_reviews';
        }

        await this.fetchPermissionMode();
        await this.fetchDepartments();
        
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
        activeTab: {
            handler(val) {
                if (val === 'my_reviews') {
                    this.fetchMyReviewTasks();
                }
            },
            immediate: true
        },
        user: {
            handler(val) {
                if (val) {
                    this.profileForm = { ...val };
                    if (['judge', 'teacher', 'college_approver', 'school_approver'].includes(val.role)) {
                        this.fetchMyReviewTasks();
                    }
                    // 已移除自动跳转到 my_reviews 的逻辑，避免覆盖用户主动导航（如个人中心）
                }
            },
            immediate: true
        },
        'awardForm.project_id': {
            handler() {
                this.autoFillAwardForm();
            }
        },
        'awardForm.stage': {
            handler() {
                this.autoFillAwardForm();
            }
        },
        'awardForm.award_level': {
            handler() {
                this.autoFillAwardForm();
            }
        },
        showAwardDialog: {
            handler(val) {
                if (val) this.$nextTick(() => this.autoFillAwardForm());
            }
        },
        'createForm.id': function(newVal, oldVal) {
             console.log(`DEBUG: createForm.id changed from ${oldVal} to ${newVal}`);
        },
        'showCreateDialog': function(val) {
            if (!val) {
                console.log('DEBUG: showCreateDialog closed. Resetting createForm to prevent state leakage.');
                this.createForm = { id: undefined, title: '', project_type: 'innovation', members: [], linked_project_id: null }; 
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
        'createForm.extra_info.is_jiebang': function(val, oldVal) {
            const v = String(val || '').trim();
            const ov = String(oldVal || '').trim();
            if (v === '是' && ov !== '是') {
                ElementPlus.ElMessage.info('已选择“揭榜挂帅”专项，可参考右侧选题库');
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
            } else if (val === 'award_mgmt' && this.canManageAwards) {
                this.fetchAwards();
            } else if (val === 'pending' && this.canManageUsers) {
                this.fetchPendingUsers();
            } else if (val === 'profile') {
                this.initProfile();
            }
        },
        searchQuery(val) {
             // trigger re-render of computed
        },
        'jiebangAdmin.keyword': function() {
            this.applyJiebangAdminFilters();
        },
        'jiebangAdmin.groupNo': function() {
            this.applyJiebangAdminFilters();
        },
        'jiebangAdmin.enabled': function() {
            this.applyJiebangAdminFilters();
        },
        'createUserForm.role'(val) {
            const mem = this.loadIdentityMemory(val);
            if (this.createUserForm && !this.createUserForm.identity_number && mem) {
                this.createUserForm.identity_number = mem;
            }
            if (this.user?.role === 'college_approver') {
                this.createUserForm.college = this.user?.college || '';
            }
        },
        'editUserForm.role'(val) {
            const mem = this.loadIdentityMemory(val);
            if (this.editUserForm && !this.editUserForm.identity_number && mem) {
                this.editUserForm.identity_number = mem;
            }
        }
    },
    methods: {
        async handleTabChange(name) {
            if (name === 'my_reviews') {
                await this.fetchMyReviewTasks();
            }
            if (name === 'advisor_review') {
                await this.fetchAdvisorPendingProjects();
            }
            if (name === 'jiebang_topics') {
                await this.fetchJiebangAdminList();
            }
            if (name === 'projects') {
                this.fetchProjects();
            }
        },
        async fetchJiebangTopicsTree() {
            if (this.jiebangTopicsLoading) return;
            this.jiebangTopicsLoading = true;
            try {
                const res = await axios.get(`/api/jiebang/topics/tree?year=${this.jiebangAdmin.year}`);
                const payload = res ? res.data : null;
                const data = payload && payload.year ? payload : (payload && payload.data ? payload.data : payload);
                this.jiebangTopicsTree = data && data.groups ? data : { year: this.jiebangAdmin.year, groups: [] };
                if (!Array.isArray(this.jiebangCollapseActive) || this.jiebangCollapseActive.length === 0) {
                    const first = (this.jiebangTopicsTree.groups || [])[0];
                    this.jiebangCollapseActive = first ? [String(first.group_no)] : [];
                }
            } catch (e) {
                console.error(e);
                this.jiebangTopicsTree = { year: this.jiebangAdmin.year, groups: [] };
            } finally {
                this.jiebangTopicsLoading = false;
            }
        },
        async fetchJiebangAdminList() {
            this.jiebangAdmin.loading = true;
            try {
                const qs = [];
                qs.push(`year=${encodeURIComponent(this.jiebangAdmin.year)}`);
                if (String(this.jiebangAdmin.enabled).trim() !== '') qs.push(`enabled=${encodeURIComponent(this.jiebangAdmin.enabled)}`);
                const res = await axios.get(`/api/jiebang/topics?${qs.join('&')}`);
                const list = Array.isArray(res.data) ? res.data : [];
                this.jiebangAdmin.rawList = list;
                this.applyJiebangAdminFilters();
            } catch (e) {
                console.error(e);
                this.jiebangAdmin.list = [];
                this.jiebangAdmin.rawList = [];
                ElementPlus.ElMessage.error(e.response?.data?.message || e.response?.data?.error || '获取选题失败');
            } finally {
                this.jiebangAdmin.loading = false;
            }
        },
        applyJiebangAdminFilters() {
            const raw = Array.isArray(this.jiebangAdmin.rawList) ? this.jiebangAdmin.rawList : [];
            const kw = String(this.jiebangAdmin.keyword || '').trim();
            const groupNo = String(this.jiebangAdmin.groupNo || '').trim();
            const enabled = String(this.jiebangAdmin.enabled || '').trim();
            this.jiebangAdmin.list = raw.filter(x => {
                if (groupNo && String(x.group_no) !== groupNo) return false;
                if (enabled !== '' && String(x.enabled) !== enabled) return false;
                if (!kw) return true;
                const s = `${x.group_name || ''} ${x.topic_title || ''} ${x.topic_desc || ''}`;
                return s.includes(kw);
            });
        },
        openJiebangTopicDialog(row) {
            const isEdit = !!(row && row.id);
            this.jiebangAdmin.isEdit = isEdit;
            if (isEdit) {
                this.jiebangAdmin.form = {
                    id: row.id,
                    year: Number(row.year || this.jiebangAdmin.year),
                    group_no: Number(row.group_no || 1),
                    group_name: String(row.group_name || ''),
                    topic_no: Number(row.topic_no || 1),
                    topic_title: String(row.topic_title || ''),
                    topic_desc: String(row.topic_desc || ''),
                    enabled: Number(row.enabled || 0) ? 1 : 0
                };
            } else {
                this.jiebangAdmin.form = {
                    id: null,
                    year: this.jiebangAdmin.year,
                    group_no: 1,
                    group_name: '',
                    topic_no: 1,
                    topic_title: '',
                    topic_desc: '',
                    enabled: 1
                };
            }
            this.jiebangAdmin.showDialog = true;
        },
        async saveJiebangTopic() {
            const f = this.jiebangAdmin.form || {};
            if (!String(f.group_name || '').trim()) {
                ElementPlus.ElMessage.warning('项目群名称为必填项');
                return;
            }
            if (!String(f.topic_title || '').trim()) {
                ElementPlus.ElMessage.warning('选题标题为必填项');
                return;
            }
            this.jiebangAdmin.loading = true;
            try {
                const payload = {
                    year: Number(f.year || this.jiebangAdmin.year),
                    group_no: Number(f.group_no || 1),
                    group_name: String(f.group_name || '').trim(),
                    topic_no: Number(f.topic_no || 1),
                    topic_title: String(f.topic_title || '').trim(),
                    topic_desc: String(f.topic_desc || '').trim(),
                    enabled: Number(f.enabled || 0) ? 1 : 0
                };
                if (this.jiebangAdmin.isEdit && f.id) {
                    await axios.put(`/api/jiebang/topics/${f.id}`, payload);
                } else {
                    await axios.post('/api/jiebang/topics', payload);
                }
                ElementPlus.ElMessage.success('保存成功');
                this.jiebangAdmin.showDialog = false;
                await this.fetchJiebangAdminList();
                await this.fetchJiebangTopicsTree();
            } catch (e) {
                console.error(e);
                ElementPlus.ElMessage.error(e.response?.data?.message || e.response?.data?.error || '保存失败');
            } finally {
                this.jiebangAdmin.loading = false;
            }
        },
        async deleteJiebangTopic(row) {
            if (!row || !row.id) return;
            try {
                await ElementPlus.ElMessageBox.confirm('确认删除该选题？', '提示', { type: 'warning' });
            } catch (e) {
                return;
            }
            this.jiebangAdmin.loading = true;
            try {
                await axios.delete(`/api/jiebang/topics/${row.id}`);
                ElementPlus.ElMessage.success('删除成功');
                await this.fetchJiebangAdminList();
                await this.fetchJiebangTopicsTree();
            } catch (e) {
                console.error(e);
                ElementPlus.ElMessage.error(e.response?.data?.message || e.response?.data?.error || '删除失败');
            } finally {
                this.jiebangAdmin.loading = false;
            }
        },
        async fetchAdvisorPendingProjects() {
            try {
                const res = await axios.get(`/api/projects/advisor-pending?t=${new Date().getTime()}`);
                this.advisorPendingProjects = res.data || [];
            } catch (e) {
                console.error('Failed to fetch advisor projects', e);
            }
        },
        openAdvisorReviewDialog(project) {
            this.currentAdvisorProject = project;
            this.advisorReviewForm = { status: 'pass', opinion: '' };
            this.showAdvisorReviewDialog = true;
        },
        async submitAdvisorReview() {
            if (!this.advisorReviewForm.opinion) {
                ElementPlus.ElMessage.warning('审批意见为必填项');
                return;
            }
            this.submittingAdvisorReview = true;
            try {
                await axios.post(`/api/projects/${this.currentAdvisorProject.id}/advisor_review`, this.advisorReviewForm);
                ElementPlus.ElMessage.success('初审操作成功');
                this.showAdvisorReviewDialog = false;
                this.advisorPendingProjects = (this.advisorPendingProjects || []).filter(p => p.id !== this.currentAdvisorProject.id);
                await this.fetchAdvisorPendingProjects();
                await this.fetchProjects();
            } catch (e) {
                ElementPlus.ElMessage.error(e.response?.data?.error || '操作失败');
            } finally {
                this.submittingAdvisorReview = false;
            }
        },
        getProjectTypeLabel(type) {
            const map = {
                'innovation': '创新训练',
                'entrepreneurship_training': '创业训练',
                'entrepreneurship_practice': '创业实践',
                'challenge_cup': '“挑战杯”全国大学生课外学术科技作品竞赛',
                'internet_plus': '中国国际大学生创新大赛',
                'youth_challenge': '“挑战杯”中国大学生创业计划竞赛',
                'three_creativity_regular': '全国大学生电子商务“创新、创意及创业”挑战赛·常规赛',
                'three_creativity_practical': '全国大学生电子商务“创新、创意及创业”挑战赛·实战赛'
            };
            return map[type] || type;
        },
        inferCompetitionTemplateType(comp) {
            if (!comp) return '';
            const tpl = (comp.template_type || '').trim();
            const known = [
                'challenge_cup',
                'internet_plus',
                'youth_challenge',
                'three_creativity_regular',
                'three_creativity_practical',
                'training',
                'innovation',
                'entrepreneurship_training',
                'entrepreneurship_practice',
                'startup'
            ];
            if (known.includes(tpl)) return tpl;
            const title = String(comp.title || '').trim();
            if (title.includes('挑战杯') && title.includes('课外学术科技作品竞赛')) return 'challenge_cup';
            if (title.includes('挑战杯') && title.includes('创业计划')) return 'youth_challenge';
            if (title.includes('电子商务') && title.includes('实战赛')) return 'three_creativity_practical';
            if (title.includes('电子商务') && (title.includes('常规赛') || title.includes('挑战赛'))) return 'three_creativity_regular';
            if (title.includes('创新大赛') || title.includes('互联网+')) return 'internet_plus';
            return '';
        },
        inferProjectTypeFromCompetition(comp) {
            if (!comp) return 'innovation';
            const sys = String(comp.system_type || '').trim();
            const title = String(comp.title || '').trim();
            if (sys === '创新体系') return 'innovation';
            if (sys === '创业体系') {
                if (title.includes('创业实践')) return 'entrepreneurship_practice';
                return 'entrepreneurship_training';
            }
            const tpl = String(comp.template_type || '').trim();
            if (['innovation', 'entrepreneurship_training', 'entrepreneurship_practice', 'challenge_cup', 'internet_plus', 'youth_challenge', 'three_creativity_regular', 'three_creativity_practical'].includes(tpl)) {
                return tpl;
            }
            return 'innovation';
        },
        getLevelLabel(level) {
            const map = {
                'national': '国家级',
                'province': '省级',
                'school': '校级',
                'college': '院级'
            };
            return map[level] || level;
        },
        // --- Profile Management ---
        async initProfile() {
            try {
                const fresh = await axios.get('/api/me');
                this.profileForm = { ...fresh.data };
                this.$emit('login-success', fresh.data);
            } catch (e) {
                if (this.user) {
                    this.profileForm = { ...this.user };
                }
            }
            if (!this.profileForm.identity_number) {
                const mem = this.loadIdentityMemory(this.profileForm.role);
                if (mem) this.profileForm.identity_number = mem;
            }
            this.passwordForm = { old_password: '', new_password: '', confirm_password: '' };
        },
        async updateProfile() {
            this.savingProfile = true;
            try {
                const keys = ['real_name', 'college', 'department', 'personal_info', 'email', 'phone', 'identity_number', 'teaching_office', 'research_area'];
                const payload = {};
                keys.forEach(k => {
                    const nv = this.profileForm?.[k];
                    const ov = this.user?.[k];
                    if (nv === '' && (ov !== '' && ov !== null && ov !== undefined)) return;
                    if (nv !== ov) payload[k] = nv;
                });
                await axios.put('/api/me', payload);
                ElementPlus.ElMessage.success('个人信息更新成功');
                const fresh = await axios.get('/api/me');
                this.$emit('login-success', fresh.data);
                this.profileForm = { ...fresh.data };
            } catch (e) {
                ElementPlus.ElMessage.error(e.message || '更新失败');
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
                const res = await axios.get('/api/legacy', { params: { keyword: this.legacyKeyword, category: this.legacyCategory || 'all' } });
                this.legacyProjects = res.data;
            } catch (e) {
                console.error(e);
            }
        },
        async borrowLegacy(row) {
            if (!row || !row.id) return;
            try {
                const res = await axios.post('/api/legacy/borrow', { legacy_id: row.id });
                const newCnt = res?.data?.borrowed_count;
                if (typeof newCnt === 'number') row.borrowed_count = newCnt;
                try { localStorage.setItem('legacy_inspiration_source_id', String(row.id)); } catch (e) {}
                ElementPlus.ElMessage.success('借鉴成功：已预选该项目思路，后续创建项目时可在“来源/灵感”中直接带入。');
            } catch (e) {
                ElementPlus.ElMessage.error(e.response?.data?.message || e.message || '借鉴失败');
            }
        },
        async adminCreateLegacy() {
            if (!this.legacyAdminForm?.original_project_id) {
                ElementPlus.ElMessage.warning('请先填写原项目ID');
                return;
            }
            if (this.adminLegacySaving) return;
            this.adminLegacySaving = true;
            try {
                const payload = {
                    original_project_id: this.legacyAdminForm.original_project_id,
                    category: this.legacyAdminForm.category
                };
                if (this.legacyAdminForm.category === 'entrepreneurship') {
                    payload.industry_field = this.legacyAdminForm.industry_field || '';
                    payload.team_experience = this.legacyAdminForm.team_experience || '';
                    payload.pitfalls = this.legacyAdminForm.pitfalls || '';
                    payload.business_model_overview = this.legacyAdminForm.business_model_overview || '';
                }
                await axios.post('/api/legacy', payload);
                ElementPlus.ElMessage.success('收录成功');
                await this.fetchLegacyProjects();
            } catch (e) {
                ElementPlus.ElMessage.error(e.response?.data?.message || e.message || '收录失败');
            } finally {
                this.adminLegacySaving = false;
            }
        },
        async searchInspiration(query) {
            if (query !== '') {
                this.inspirationLoading = true;
                try {
                    const res = await axios.get('/api/legacy', { params: { keyword: query, category: 'all' } });
                    this.inspirationOptions = res.data.map(item => ({
                        value: item.id,
                        label: item.title,
                        summary: item.methodology_summary || item.business_model_overview || item.team_experience || item.pitfalls || ''
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
                    ? res.data : [];
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
                    ? res.data : [];
                
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
        async fetchPermissionMode() {
            try {
                const res = await axios.get('/api/permission-mode');
                const mode = res.data?.mode;
                this.permissionMode = mode === 'strict' ? 'strict' : 'mixed';
                this.permissionModeDraft = this.permissionMode;
            } catch (e) {
                this.permissionMode = 'mixed';
                this.permissionModeDraft = 'mixed';
            }
        },
        async fetchDepartments() {
            const majors = [];
            for (const k of Object.keys(CNMU_COLLEGE_MAJOR)) {
                const arr = CNMU_COLLEGE_MAJOR[k];
                if (Array.isArray(arr)) {
                    for (const m of arr) {
                        if (m) majors.push(m);
                    }
                }
            }
            this.departments = Array.from(new Set(majors)).sort();
        },
        async confirmPermissionModeChange() {
            const newMode = this.permissionModeDraft;
            const oldMode = this.permissionMode;
            if (newMode === oldMode) return;

            const newLabel = newMode === 'strict' ? '严格模式' : '混合模式';
            const oldLabel = oldMode === 'strict' ? '严格模式' : '混合模式';
            const impact = newMode === 'strict'
                ? '切换为严格模式后，学校管理员/学院管理员将失去用户管理权限（增删改查/审核等），仅系统管理员保留。'
                : '切换为混合模式后，学校管理员可管理全校用户，学院管理员可管理本院用户。';

            try {
                await ElementPlus.ElMessageBox.confirm(
                    `确认从【${oldLabel}】切换到【${newLabel}】？\n\n${impact}`,
                    '确认切换权限模式',
                    { type: 'warning', confirmButtonText: '确认切换', cancelButtonText: '取消' }
                );

                await axios.post('/api/settings', { permission_mode: newMode });
                await this.fetchPermissionMode();
                ElementPlus.ElMessage.success('权限模式已更新并立即生效');
            } catch (e) {
                this.permissionModeDraft = this.permissionMode;
            }
        },
        async fetchStats() {
            this.loadingStats = true;
            try {
                const res = await axios.get('/api/stats');
                this.systemStats = res.data?.data || res.data || {};
                this.$nextTick(() => {
                    this.renderCharts();
                });
            } catch(e) {
                console.error(e);
                ElementPlus.ElMessage.error(e.response?.data?.message || e.response?.data?.error || '获取统计数据失败');
                this.systemStats = { project_stats: [], type_stats: [], college_stats: [] };
            }
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
                            data: (this.systemStats.project_stats || []).map(s => ({ value: s.count, name: this.getStatusInfo(s.status).text }))
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
                            data: (this.systemStats.type_stats || []).map(s => ({ value: s.count, name: getTypeLabel(s.project_type) })),
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
                    xAxis: [ { type: 'category', data: (this.systemStats.college_stats || []).map(s => s.college), axisTick: { alignWithLabel: true }, axisLabel: { rotate: 45, interval: 0 } } ],
                    yAxis: [ { type: 'value' } ],
                    series: [
                        {
                            name: '项目数量',
                            type: 'bar',
                            barWidth: '60%',
                            data: (this.systemStats.college_stats || []).map(s => s.count)
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
                const res = await axios.get('/api/stats');
                this.systemStats = res.data?.data || res.data || {};
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
                }
                // Filter out invalid projects
                this.projects = Array.isArray(res.data) 
                    ? res.data.filter(p => p && p.id && !isNaN(Number(p.id)) && Number(p.id) > 0) 
                    : [];
                this.syncCompetitionProjectMapping();
                
                // Legacy Prompt Check
                if (this.user?.role === 'student') {
                    const candidate = this.projects.find(p => 
                        (
                            p.status === 'finished' ||
                            (
                                p.national_award_level &&
                                String(p.national_award_level).trim() !== 'none'
                            )
                        ) &&
                        (!p.extra_info || !p.extra_info.legacy_prompted) &&
                        p.created_by === this.user?.id
                    );
                    
                    if (candidate) {
                        const tplName = candidate.resolved_template_name || candidate.template_type || candidate.project_type || '';
                        const category = ['大挑', '“挑战杯”全国大学生课外学术科技作品竞赛', 'challenge_cup', '大创创新训练'].includes(tplName) ? 'innovation' : 'entrepreneurship';
                        
                        const finalizePrompt = async () => {
                            const extra = candidate.extra_info || {};
                            extra.legacy_prompted = true;
                            await axios.put(`/api/projects/${candidate.id}`, { extra_info: extra });
                        };

                        if (category === 'innovation') {
                            try {
                                await ElementPlus.ElMessageBox.confirm(
                                    `恭喜！你的项目《${candidate.title}》已结题/获奖。是否同意将本项目的经验总结收录至往届经验库？\n\n系统将自动生成方法论总结，并对专家评语进行脱敏处理（去掉人名、单位）。`,
                                    '经验传承',
                                    {
                                        confirmButtonText: '同意收录',
                                        cancelButtonText: '暂不收录',
                                        type: 'success'
                                    }
                                );
                                
                                await axios.post('/api/legacy', {
                                    original_project_id: candidate.id,
                                    category: 'innovation'
                                });
                                
                                ElementPlus.ElMessage.success('收录成功！感谢你的贡献。');
                            } catch (e) {
                                // cancel: pass
                            } finally {
                                await finalizePrompt();
                            }
                        } else {
                            // 创业类由管理员手动脱敏后收录
                            await finalizePrompt();
                        }
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
        isProcessStatusCompleted(status) {
            if (!status) return false;
            const s = String(status).trim();
            if (!s) return false;
            if (s.startsWith('待')) return false;
            if (s.includes('评审中') || s.includes('审核中') || s.includes('进行中')) return false;
            if (s.includes('未') || s.includes('驳回') || s.includes('不通过')) return false;
            return true;
        },
        isProcessNodeCompleted(nodeName) {
            const s = this.projectProcess?.node_current_status ? this.projectProcess.node_current_status[nodeName] : null;
            return this.isProcessStatusCompleted(s);
        },
        getProcessActiveStep() {
            if (!this.projectProcess || !this.projectProcess.process_structure) return 0;
            let active = 0;
            for (let i = 0; i < this.projectProcess.process_structure.length; i++) {
                const node = this.projectProcess.process_structure[i];
                const st = this.projectProcess.node_current_status ? this.projectProcess.node_current_status[node] : null;
                if (this.isProcessStatusCompleted(st)) {
                    active = i + 1;
                } else {
                    break;
                }
            }
            return active;
        },
        shouldShowProcessMaterials() {
            const tpl = this.projectProcess?.template_name;
            return ['大创创新训练', '大创创业训练', '大创创业实践'].includes(tpl);
        },
        isProcessNodeUnlocked(index) {
            if (index === 0) return true; // 第一个节点永远解锁
            if (!this.projectProcess || !this.projectProcess.process_structure) return false;
            
            const prevNode = this.projectProcess.process_structure[index - 1];
            const prevStatus = this.projectProcess.node_current_status ? this.projectProcess.node_current_status[prevNode] : null;
            
            return this.isProcessStatusCompleted(prevStatus);
        },
        handleProcessUpload(event, stage, type) {
            const file = event.target.files[0];
            if (!file) return;
            if (stage === 'methodology' && (type === 'route_map' || type === 'photo')) {
                if (!String(file.type || '').startsWith('image/')) {
                    ElementPlus.ElMessage.error('请上传图片文件');
                    event.target.value = '';
                    return;
                }
            }
            
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
                event.target.value = ''; // Reset input
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

        openUrl(url) {
            if (!url) return;
            window.open(url, '_blank');
        },
        getExperienceMaterialRows() {
            const files = Array.isArray(this.currentProject?.files) ? this.currentProject.files : [];
            const ei = this.currentProject?.extra_info || {};
            const appDoc = ei?.attachments?.application_doc;
            
            const latestByType = (t) => {
                const list = files.filter(f => f && f.file_type === t && f.file_path);
                return list.length ? list[0].file_path : '';
            };
            
            const researchUrl = latestByType('conclusion');
            const methodologyUrl = latestByType('methodology');
            const researchSummary = (this.currentProject?.abstract || '').trim();
            
            const coreKeys = ['project_goal', 'project_overview', 'innovation_points', 'expected_results', 'background', 'problem', 'solution'];
            const coreParts = [];
            coreKeys.forEach(k => {
                const v = ei?.[k];
                if (v && String(v).trim()) coreParts.push(`${k}: ${String(v).trim()}`);
            });
            
            return [
                { name: '方法论材料', url: methodologyUrl, desc: '大挑参赛技术/研究方法论材料（学生提交的富文本总结将用于经验库审核）' },
                { name: '研究报告/论文', url: researchUrl, desc: `大挑官方要求的学术论文/调查报告/技术报告核心摘要：${researchSummary || '—'}` },
                { name: '申报书', url: appDoc, desc: coreParts.length ? `大挑校级申报书核心内容（脱敏后展示）：\n${coreParts.join('\n')}` : '大挑校级申报书核心内容（脱敏后展示）：—' }
            ];
        },
        getWorkCategoryLabel(v) {
            const s = String(v || '').trim();
            const map = {
                'science_paper': '自然科学类学术论文',
                'social_report': '哲学社科类调查报告',
                'tech_invention': '科技发明制作',
                'natural_science': '自然科学类学术论文',
                'philosophy_social_science': '哲学社科类调查报告',
                'science_invention': '科技发明制作'
            };
            return map[s] || s || '';
        },
        getLegacyAuditText() {
            const st = String(this.currentProject?.legacy_status || '').trim();
            if (st === 'pending') return '待大挑校级组委会审核';
            if (st === 'approved') return this.currentProject?.legacy_is_public ? '已入库（已公开）' : '已入库（未公开）';
            if (st === 'rejected') return '已驳回（请按大挑规范修改后重新提交）';
            if (this.currentProject?.extra_info?.experience_status === 'submitted') return '待大挑校级组委会审核';
            return '未提交';
        },
        getLegacyAuditTagType() {
            const st = String(this.currentProject?.legacy_status || '').trim();
            if (st === 'approved') return 'success';
            if (st === 'rejected') return 'danger';
            if (st === 'pending') return 'warning';
            if (this.currentProject?.extra_info?.experience_status === 'submitted') return 'warning';
            return 'info';
        },
        getDachuangExpertReviews() {
            const list = Array.isArray(this.currentProject?.reviews) ? this.currentProject.reviews : [];
            return list.filter(x => x && String(x.comment || '').trim());
        },
        stripHtml(html) {
            const div = document.createElement('div');
            div.innerHTML = String(html || '');
            return (div.textContent || div.innerText || '').replace(/\s+/g, ' ').trim();
        },
        getEditorTextLen(key) {
            const txt = this.stripHtml(this.methodologySections?.[key] || '');
            return txt.replace(/\s+/g, '').length;
        },
        getEditorLimit(key) {
            const map = { bg: 100, process: 150, innovation: 100, effect: 100, norm: 50 };
            return map[key] || 0;
        },
        onEditorInput(key, e) {
            this.methodologySections[key] = e?.target?.innerHTML || '';
        },
        formatEditor(cmd) {
            try {
                document.execCommand(cmd, false, null);
            } catch (e) {}
        },
        buildMethodologyPlainText() {
            const bg = this.stripHtml(this.methodologySections.bg);
            const proc = this.stripHtml(this.methodologySections.process);
            const inov = this.stripHtml(this.methodologySections.innovation);
            const eff = this.stripHtml(this.methodologySections.effect);
            const norm = this.stripHtml(this.methodologySections.norm);
            return [
                `1. 选题背景与科学问题：${bg}`,
                `2. 研究/设计方法与过程：${proc}`,
                `3. 核心创新点与突破：${inov}`,
                `4. 应用价值与实践前景：${eff}`,
                `5. 规范性说明：${norm}`
            ].join('\n');
        },
        canSubmitDachuangExperience() {
            const st = String(this.currentProject?.legacy_status || '').trim();
            if (st === 'approved' || st === 'pending') return false;
            if (this.currentProject?.extra_info?.experience_status === 'submitted' && st !== 'rejected') return false;
            return true;
        },
        async submitMethodologyRich() {
            if (!this.currentProject?.id) {
                ElementPlus.ElMessage.error('项目ID缺失，请重新打开详情页');
                return;
            }
            if (!this.canSubmitDachuangExperience()) {
                ElementPlus.ElMessage.warning('当前状态不允许重复提交');
                return;
            }
            if (this.currentProject?.project_type === 'challenge_cup') {
                const hasRoute = String(this.processFiles?.methodology?.route_map || '').trim();
                if (!hasRoute) {
                    ElementPlus.ElMessage.warning('大挑项目技术路线图/研究框架图为必传材料');
                    return;
                }
            }
            const keys = ['bg', 'process', 'innovation', 'effect', 'norm'];
            const keyName = { bg: '模块1', process: '模块2', innovation: '模块3', effect: '模块4', norm: '模块5' };
            for (const k of keys) {
                const limit = this.getEditorLimit(k);
                const len = this.getEditorTextLen(k);
                if (limit && len > limit) {
                    ElementPlus.ElMessage.warning(`${keyName[k] || k} 超出字数限制（${len}/${limit}）`);
                    return;
                }
            }
            const plain = this.buildMethodologyPlainText();
            const stripped = plain.replace(/\s+/g, '').replace(/[0-9]\./g, '');
            if (!stripped) {
                ElementPlus.ElMessage.warning('富文本内容不能为空');
                return;
            }
            this.submittingMethodology = true;
            try {
                const attachments = this.processFiles.methodology || {};
                await axios.post(`/api/projects/${this.currentProject.id}/methodology`, {
                    sections: this.methodologySections,
                    summary: plain,
                    attachments
                });
                ElementPlus.ElMessage.success('提交成功');
                await this.viewDetails(this.currentProject.id);
                this.detailActiveTab = 'audit';
            } catch (e) {
                ElementPlus.ElMessage.error(e.response?.data?.error || e.response?.data?.message || e.message || '提交失败');
            } finally {
                this.submittingMethodology = false;
            }
        },
        async submitMethodology() {
            if (!this.currentProject?.id) {
                ElementPlus.ElMessage.error('项目ID缺失，请重新打开详情页');
                return;
            }
            const summary = (this.methodologySummary || '').trim();
            if (!summary) {
                ElementPlus.ElMessage.warning('方法论总结不能为空');
                return;
            }
            this.submittingMethodology = true;
            try {
                const attachments = this.processFiles.methodology || {};
                await axios.post(`/api/projects/${this.currentProject.id}/methodology`, { summary, attachments });
                ElementPlus.ElMessage.success('提交成功');
                await this.viewDetails(this.currentProject.id);
                this.detailActiveTab = 'audit';
            } catch (e) {
                ElementPlus.ElMessage.error(e.response?.data?.error || e.response?.data?.message || e.message || '提交失败');
            } finally {
                this.submittingMethodology = false;
            }
        },

        async fetchProjectProcess(projectId) {
            if (!projectId) {
                this.projectProcess = null;
                return;
            }
            this.projectProcessLoading = true;
            try {
                const res = await axios.get(`/api/projects/${projectId}/process`);
                const data = res.data || {};
                if (!data.node_status_options && data.node_status_options) data.node_status_options = data.node_status_options;
                if (!data.node_status_options) data.node_status_options = {};
                if (!data.node_current_status) data.node_current_status = {};
                if (!data.node_comments) data.node_comments = {};
                if (!data.node_award_levels) data.node_award_levels = {};
                const nodes = Array.isArray(data.process_structure) ? data.process_structure : [];
                nodes.forEach(n => {
                    if (data.node_current_status[n] === undefined || data.node_current_status[n] === null) data.node_current_status[n] = '';
                    if (data.node_comments[n] === undefined || data.node_comments[n] === null) data.node_comments[n] = '';
                    if (data.node_award_levels[n] === undefined || data.node_award_levels[n] === null) data.node_award_levels[n] = '';
                });
                this.projectProcess = data;
            } catch (e) {
                console.error(e);
                this.projectProcess = null;
            } finally {
                this.projectProcessLoading = false;
            }
        },

        canEditProcessNode() {
            const role = this.user?.role;
            return !!role && ['project_admin', 'system_admin'].includes(role);
        },
        async saveProcessNode(nodeName) {
            if (!this.currentProject?.id || !this.projectProcess?.node_current_status) return;
            const dataToSend = {
                node_name: nodeName,
                current_status: this.projectProcess.node_current_status[nodeName] || '',
                comment: (this.projectProcess.node_comments && this.projectProcess.node_comments[nodeName]) ? this.projectProcess.node_comments[nodeName] : '',
                award_level: (this.projectProcess.node_award_levels && this.projectProcess.node_award_levels[nodeName]) ? this.projectProcess.node_award_levels[nodeName] : ''
            };
            console.log('DEBUG: Saving process node:', dataToSend);
            this.projectProcessSaving[nodeName] = true;
            try {
                await axios.put(`/api/projects/${this.currentProject.id}/process`, dataToSend);
                ElementPlus.ElMessage.success('保存成功');
                await this.fetchProjectProcess(this.currentProject.id);
                await this.fetchProjects();
                await this.viewDetails(this.currentProject.id);
                await this.fetchNotifications();
            } catch (e) {
                ElementPlus.ElMessage.error(e.response?.data?.error || '保存失败');
            } finally {
                this.projectProcessSaving[nodeName] = false;
            }
        },

        shouldShowCollegeRecommendationPanel() {
            if (this.user?.role !== 'college_approver') return false;
            const tpl = this.projectProcess?.template_name || '';
            if (tpl !== '大创创新训练') return false;
            return true;
        },
        async submitCollegeRecommendation(action) {
            if (!this.currentProject?.id) return;
            this.collegeRecSaving = true;
            try {
                const payload = {
                    action,
                    passed: this.collegeRecForm.passed,
                    feedback: this.collegeRecForm.feedback,
                    defense_score: this.collegeRecForm.defense_score,
                    recommend_rank: this.collegeRecForm.recommend_rank,
                    is_key_support: this.collegeRecForm.is_key_support ? 1 : 0
                };
                await axios.put(`/api/projects/${this.currentProject.id}/college-recommendation`, payload);
                ElementPlus.ElMessage.success('已提交');
                await this.fetchProjects();
                await this.viewDetails(this.currentProject.id);
                await this.fetchProjectProcess(this.currentProject.id);
            } catch (e) {
                ElementPlus.ElMessage.error(e.response?.data?.message || e.response?.data?.error || '提交失败');
            } finally {
                this.collegeRecSaving = false;
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
                'finished': { text: '已结项', type: 'success' },
                'finished_national_award': { text: '已结项·国赛获奖', type: 'success' }
            };
            return map[status] || STATUS_MAP[status] || { text: status, type: 'info' };
        },
        getStatusText(status) { return this.getStatusInfo(status).text; },
        getStatusType(status) { return this.getStatusInfo(status).type; },
        // 根据“项目的实际状态字段组合”（例如赛事获奖录入）计算状态标签颜色
        getStatusTypeForRow(row) {
            const text = this.getStatusTextForRow(row);
            if (text === '已结项·国赛获奖' || text === '国赛获奖' || text === '省赛获奖') return 'success';
            if (typeof text === 'string' && text.endsWith('已驳回')) return 'danger';
            return this.getStatusType(row.status);
        },
        getAwardLevelLabel(level) {
            if (!level || level === 'none') return '';
            const map = {
                'gold': '金奖',
                'silver': '银奖',
                'bronze': '铜奖',
                'special': '特等奖',
                'first': '一等奖',
                'second': '二等奖',
                'third': '三等奖',
                'excellent': '优秀奖'
            };
            return map[level] || level;
        },
        getAwardStageLabel(stage) {
            const s = String(stage || '').trim();
            if (s === 'provincial') return '省赛';
            if (s === 'national') return '国赛';
            return s;
        },
        getCompetitionKeyFromProject(project) {
            if (!project) return '';
            const keys = ['challenge_cup', 'internet_plus', 'youth_challenge', 'three_creativity_regular', 'three_creativity_practical'];
            const direct = String(project.project_type || project.template_type || '').trim();
            if (keys.includes(direct)) return direct;
            const resolved = String(project.resolved_template_name || project.template_name || '').trim();
            if (resolved === '“挑战杯”全国大学生课外学术科技作品竞赛' || resolved === '大挑') return 'challenge_cup';
            if (resolved === '“挑战杯”中国大学生创业计划竞赛' || resolved === '小挑') return 'youth_challenge';
            if (resolved === '中国国际大学生创新大赛' || resolved === '国创赛') return 'internet_plus';
            if (resolved === '全国大学生电子商务“创新、创意及创业”挑战赛·常规赛' || resolved === '三创赛常规赛') return 'three_creativity_regular';
            if (resolved === '全国大学生电子商务“创新、创意及创业”挑战赛·实战赛' || resolved === '三创赛实战赛') return 'three_creativity_practical';
            const title = String(project.competition_title || '').trim();
            if (title.includes('中国国际大学生创新大赛') || title.includes('创新大赛') || title.includes('互联网+')) return 'internet_plus';
            if (title.includes('创业计划') && title.includes('挑战杯')) return 'youth_challenge';
            if (title.includes('课外学术科技作品') && title.includes('挑战杯')) return 'challenge_cup';
            if (title.includes('电子商务') && (title.includes('常规赛') || title.includes('挑战赛'))) return 'three_creativity_regular';
            if (title.includes('电子商务') && title.includes('实战赛')) return 'three_creativity_practical';
            return '';
        },
        getAwardIssuer(project, stage) {
            const key = this.getCompetitionKeyFromProject(project);
            const st = String(stage || '').trim();
            const map = {
                internet_plus: { provincial: '省教育厅', national: '教育部等12部门' },
                challenge_cup: { provincial: '团省委、省教育厅等', national: '团中央、中国科协、教育部等' },
                youth_challenge: { provincial: '团省委、省教育厅等', national: '团中央、教育部等' },
                three_creativity_regular: { provincial: '省三创赛组委会', national: '全国电子商务产教融合创新联盟、西安交通大学' },
                three_creativity_practical: { provincial: '省三创赛组委会', national: '全国电子商务产教融合创新联盟、西安交通大学' }
            };
            const hit = map[key];
            if (hit && hit[st]) return hit[st];
            return '';
        },
        getAwardDialogCompetitionName(project) {
            if (!project) return '';
            const t = String(project.competition_title || '').trim();
            if (t) return t;
            const resolved = String(project.resolved_template_name || project.template_name || '').trim();
            if (resolved) return resolved;
            const ptype = String(project.project_type || '').trim();
            return this.getProjectTypeLabel(ptype);
        },
        getDefaultAwardTime(project) {
            const d = new Date();
            const m = String(d.getMonth() + 1).padStart(2, '0');
            const y = String(project?.year || d.getFullYear()).trim() || String(d.getFullYear());
            return `${y}-${m}`;
        },
        getDefaultAwardName(project, stage, awardLevel) {
            const comp = this.getAwardDialogCompetitionName(project);
            const st = this.getAwardStageLabel(stage);
            const lv = this.getAwardLevelLabel(awardLevel);
            const parts = [];
            if (comp) parts.push(comp);
            if (st) parts.push(st);
            if (lv) parts.push(lv);
            return parts.join('');
        },
        autoFillAwardForm() {
            if (!this.awardForm || !this.showAwardDialog) return;
            const p = this.getAwardDialogProject();
            if (!p) return;
            const nextName = this.getDefaultAwardName(p, this.awardForm.stage, this.awardForm.award_level);
            const nextTime = this.getDefaultAwardTime(p);
            const nextIssuer = this.getAwardIssuer(p, this.awardForm.stage);
            const curName = String(this.awardForm.award_name || '');
            const curTime = String(this.awardForm.award_time || '');
            const curIssuer = String(this.awardForm.issuer || '');
            if ((!curName || curName === this.awardAuto.name) && nextName) {
                this.awardForm.award_name = nextName;
                this.awardAuto.name = nextName;
            }
            if ((!curTime || curTime === this.awardAuto.time) && nextTime) {
                this.awardForm.award_time = nextTime;
                this.awardAuto.time = nextTime;
            }
            if ((!curIssuer || curIssuer === this.awardAuto.issuer) && nextIssuer) {
                this.awardForm.issuer = nextIssuer;
                this.awardAuto.issuer = nextIssuer;
            }
        },
        getDynamicAwardOptions(project) {
            if (!project) return [];
            const tplName = project.resolved_template_name || project.template_type || project.project_type;
            if ([
                '大挑', '“挑战杯”全国大学生课外学术科技作品竞赛', 'challenge_cup',
                '国创赛', '中国国际大学生创新大赛', 'internet_plus',
                '小挑', '“挑战杯”中国大学生创业计划竞赛', 'youth_challenge',
                '三创赛常规赛', '全国大学生电子商务“创新、创意及创业”挑战赛·常规赛', 'three_creativity_regular',
                '三创赛实战赛', '全国大学生电子商务“创新、创意及创业”挑战赛·实战赛', 'three_creativity_practical'
            ].includes(tplName)) {
                return ["special", "first", "second", "third"];
            }
            if (['大创创新训练', '大创创业训练', '大创创业实践'].includes(tplName)) {
                return ["优秀", "良好", "合格", "不合格"];
            }
            return [];
        },
        getAwardOptionsWithCurrent(project, field) {
            const base = this.getDynamicAwardOptions(project) || [];
            const current = (project && project[field]) ? String(project[field]).trim() : '';
            if (!current || current === 'none') return base;
            return base.includes(current) ? base : [current, ...base];
        },
        getAwardDialogProject() {
            const pid = this.awardForm?.project_id;
            if (!pid) return this.currentProject || null;
            const p = (this.projects || []).find(x => Number(x.id) === Number(pid));
            return p || this.currentProject || null;
        },
        getStatusTextForRow(row) {
            let base = this.getStatusInfo(row.status).text;
            const tplName = row.resolved_template_name || row.template_type || row.project_type;
            if ((row.project_type === 'entrepreneurship_training' || row.project_type === 'entrepreneurship_practice') && row.status === 'pending_college') {
                const qualified = Number(row.extra_info?.college_qualified || 0);
                if (qualified === 1) base = '待学校评审';
            }
            if (tplName === '大挑' || tplName === '“挑战杯”全国大学生课外学术科技作品竞赛' || tplName === 'challenge_cup' || row.project_type === 'challenge_cup') {
                const cr = (row.college_review_result || '').trim();
                const sr = (row.school_review_result || '').trim();
                const lv = (row.current_level || '').trim();
                const natStatus = (row.national_status || '').trim();
                const natAwardLevel = (row.national_award_level || '').trim();
                const provStatus = (row.provincial_status || '').trim();
                const provAwardLevel = (row.provincial_award_level || '').trim();
                const hasNationalAward = (natAwardLevel && natAwardLevel !== 'none');
                const hasProvincialAward = (provAwardLevel && provAwardLevel !== 'none');
                
                if (row.status === 'finished_national_award') return '已结项·国赛获奖';
                if (natStatus === '已获奖' || hasNationalAward) return '国赛获奖';
                if (provStatus === '已获奖' || hasProvincialAward) return '省赛获奖';
                if (lv === 'national' || row.provincial_advance_national) return '待处理（国赛）';
                if (sr === 'approved' || lv === 'provincial') return '待处理（省赛）';
                if (sr === 'rejected') return '校赛未推荐';
                if (cr === 'rejected') return '学院赛未推荐';
            }
            
            // 针对不需要导师审核的赛事类项目，如果是pending/under_review，修正显示名称
            if (!this.isTemplateNeedingTeacherAudit(row)) {
                if (row.status === 'pending' || row.status === 'under_review') {
                    if (row.current_level === 'national') base = '待处理（国赛）';
                    else if (row.current_level === 'provincial') base = '待处理（省赛）';
                    else if (row.current_level === 'school') base = '待评审（校赛）';
                    else base = '待评审（学院赛）';
                }

                // 赛事获奖结果录入后，直接展示“国赛获奖”（学生侧你关心的状态显示）
                const natStatus = (row.national_status || '').trim();
                const natAwardLevel = (row.national_award_level || '').trim();
                const provStatus = (row.provincial_status || '').trim();
                const provAwardLevel = (row.provincial_award_level || '').trim();

                const hasNationalAward = (natAwardLevel && natAwardLevel !== 'none');
                const hasProvincialAward = (provAwardLevel && provAwardLevel !== 'none');

                if (row.status === 'finished_national_award') base = '已结项·国赛获奖';
                else if (natStatus === '已获奖' || hasNationalAward) base = '国赛获奖';
                else if (provStatus === '已获奖' || hasProvincialAward) base = '省赛获奖';
            }

            const isRejected = row.status === 'rejected' || (typeof row.status === 'string' && row.status.endsWith('_rejected'));
            if (!isRejected) return base;
            const level = row.extra_info?.rejection_level
                || (row.school_feedback ? '学校' : (row.college_feedback ? '学院' : (row.extra_info?.advisor_feedback ? '学院（导师）' : '')));
            return level ? `${level}已驳回` : base;
        },
        
        // --- Permissions ---
        isTemplateNeedingTeacherAudit(project) {
            if (!project) return false;
            // 优先使用后端解析好的准确模板名
            const tplName = project.resolved_template_name || project.template_type || project.project_type;
            const title = project.competition_title || project.title || '';
            
            // 只要是这些大创或大挑相关的类型或标题包含，就需要导师审批
            if (['大创创新训练', '大创创业训练', '大创创业实践', 'innovation_training', 'entrepreneurship_training', 'entrepreneurship_practice', 'innovation', 'training', '大挑', '“挑战杯”全国大学生课外学术科技作品竞赛', 'challenge_cup'].includes(tplName)) {
                return true;
            }
            if (title.includes('大创') || title.includes('创新训练') || title.includes('创业训练') || title.includes('创业实践') || title.includes('挑战杯')) {
                return true;
            }
            return false;
        },
        canUserAudit(project) {
            const role = this.user?.role;
            if (!role) return false;
            const status = project.status;
            
            // 学院管理员：管理大创项目审核 (学院评审)
            if (role === 'college_approver') {
                return ['pending_college', 'advisor_approved', 'midterm_advisor_approved', 'conclusion_advisor_approved'].includes(status);
            }
            // 学校管理员：管理大创终审 (学校立项 / 终审)
            if (role === 'school_approver') {
                return ['college_recommended', 'pending_college', 'college_approved', 'midterm_college_approved', 'conclusion_college_approved'].includes(status);
            }
            // 指导老师：大创/大挑项目初审
            if (role === 'teacher') {
                return ['pending_teacher', 'pending', 'pending_advisor_review', 'midterm_submitted', 'conclusion_submitted'].includes(status);
            }
            return false;
        },
        canEditProcessNodeFor(nodeName) {
            if (!this.canEditProcessNode()) return false;
            const role = this.user?.role;
            const tplName = this.projectProcess?.template_name;

            // 学院管理员：管理大挑学院赛评审
            if ((tplName === '大挑' || tplName === '“挑战杯”全国大学生课外学术科技作品竞赛') && nodeName === '学院赛') {
                return ['college_approver', 'project_admin', 'system_admin'].includes(role);
            }
            // 学校管理员：管理大挑校赛/省赛/国赛结果录入
            if ((tplName === '大挑' || tplName === '“挑战杯”全国大学生课外学术科技作品竞赛') && ['校赛', '省赛', '国赛'].includes(nodeName)) {
                return ['school_approver', 'project_admin', 'system_admin'].includes(role);
            }
            // 其他赛事（国创赛、小挑、三创赛）：统一由学校管理员管理校/省/国赛结果
            if ([
                '国创赛', '中国国际大学生创新大赛', 'internet_plus',
                '小挑', '“挑战杯”中国大学生创业计划竞赛', 'youth_challenge',
                '三创赛常规赛', '全国大学生电子商务“创新、创意及创业”挑战赛·常规赛', 'three_creativity_regular',
                '三创赛实战赛', '全国大学生电子商务“创新、创意及创业”挑战赛·实战赛', 'three_creativity_practical'
            ].includes(tplName)) {
                return ['school_approver', 'project_admin', 'system_admin'].includes(role);
            }
            
            return ['project_admin', 'system_admin'].includes(role);
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
            return this.user?.role === 'judge' && ['reviewing', 'school_approved', 'rated'].includes(project.status);
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
                const path = res && res.data && res.data.path;
                if (path) {
                    try {
                        const dl = await axios.get(path, { responseType: 'blob' });
                        const blobUrl = window.URL.createObjectURL(dl.data);
                        try {
                            const a = document.createElement('a');
                            a.href = blobUrl;
                            a.download = (path.split('/').pop() || 'database.db');
                            document.body.appendChild(a);
                            a.click();
                            a.remove();
                            ElementPlus.ElMessage.success('已开始下载');
                        } finally {
                            window.URL.revokeObjectURL(blobUrl);
                        }
                    } catch (e) {
                        ElementPlus.ElMessage.error(e.response?.data?.error || '下载失败');
                    }
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
            const v = key.split('.').reduce((obj, i) => obj ? obj[i] : undefined, form);
            return (v === undefined || v === null) ? '' : v;
        },
        shouldShow(form, item) {
            const rule = item && item.show_if;
            if (!rule) return true;
            const v = this.getFieldValue(form, rule.key);
            const values = Array.isArray(rule.values) ? rule.values : [];
            return values.includes(v);
        },
        getTableRows(form, key) {
            const v = this.getFieldValue(form, key);
            if (Array.isArray(v)) return v;
            if (typeof v === 'string') {
                const s = v.trim();
                if (!s) return [];
                try {
                    const parsed = JSON.parse(s);
                    return Array.isArray(parsed) ? parsed : [];
                } catch (e) {
                    return [];
                }
            }
            return [];
        },
        isCollaboratorsTableKey(key) {
            const k = String(key || '').trim();
            return k === 'extra_info.collaborators_individual' || k === 'extra_info.collaborators_team';
        },
        isCollaboratorsTableField(field) {
            return this.isCollaboratorsTableKey(field?.key);
        },
        getCollaboratorsColumns() {
            return [
                { label: '姓名', key: '姓名', width: 90 },
                { label: '学号', key: '学号', width: 110 },
                { label: '学历', key: '学历', width: 90 },
                { label: '专业', key: '专业', width: 100 },
                { label: '学院', key: '学院', width: 120 },
                { label: '承担工作', key: '承担工作', width: 160 }
            ];
        },
        getEffectiveTableColumns(field) {
            return [
                { "label": "测试列", "key": "test", "width": 100 }
            ];
        },
            
            // 更加宽松的匹配逻辑，确保所有包含 member 关键字的表格都使用统一列配置
            if (k === 'members' || k.includes('member')) {
                const cols = [
                    { "label": "学号", "key": "student_id", "width": 140 },
                    { "label": "姓名", "key": "name", "width": 100 },
                    { "label": "学院", "key": "college", "width": 150 },
                    { "label": "年级", "key": "grade", "width": 100 },
                    { "label": "专业", "key": "major", "width": 160 },
                    { "label": "角色", "key": "role", "width": 120 }
                ];
                console.log('Returning forced columns for members:', cols);
                return cols;
            }

            if (Array.isArray(field.columns) && field.columns.length > 0) return field.columns;
            // Fallback for fields that might have columns in options (legacy)
            if (Array.isArray(field.options) && field.type === 'table') return field.options;
            return [];
        },
        getCollaboratorsLimit(form, fieldKey) {
            const t = String(this.getFieldValue(form, 'extra_info.declaration_type') || '').trim();
            if (t === 'individual') return 2;
            if (t === 'team') return 8;
            const k = String(fieldKey || '').trim();
            if (k.endsWith('_individual')) return 2;
            if (k.endsWith('_team')) return 8;
            return 8;
        },
        getCollaboratorsLimitHint(form, fieldKey) {
            const t = String(this.getFieldValue(form, 'extra_info.declaration_type') || '').trim();
            if (t === 'individual') return '人数限制：个人项目 ≤ 2 人';
            if (t === 'team') return '人数限制：集体项目 ≤ 8 人';
            const limit = this.getCollaboratorsLimit(form, fieldKey);
            return `人数限制：≤ ${limit} 人`;
        },
        addTableRowSmart(form, field) {
            const columns = this.getEffectiveTableColumns(field);
            if (this.isCollaboratorsTableField(field)) {
                const rows = this.getTableRows(form, field.key);
                const limit = this.getCollaboratorsLimit(form, field.key);
                if (rows.length >= limit) {
                    ElementPlus.ElMessage.warning(`人数上限为 ${limit} 人`);
                    return;
                }
            }
            this.addTableRow(form, field.key, columns);
        },
        addTableRow(form, key, columns) {
            const rows = this.getTableRows(form, key);
            const row = {};
            (columns || []).forEach(c => { row[c.key] = ''; });
            if (String(key || '').trim() === 'members') {
                row.role = 'member';
                row.college = row.college || this.getFieldValue(form, 'extra_info.leader_info.college') || (this.user?.college || '');
                row.grade = row.grade || '';
                row.major = row.major || '';
            }
            rows.push(row);
            this.setFieldValue(form, key, rows);
        },
        isLeaderMemberRow(row) {
            const r = row || {};
            const role = String(r.role || '').trim();
            if (role === 'leader') return true;
            if (role === '负责人') return true;
            if (Number(r.is_leader || 0) === 1) return true;
            return false;
        },
        getMemberMajorOptions(row) {
            const c = String((row && row.college) || '').trim();
            const arr = CNMU_COLLEGE_MAJOR[c];
            return Array.isArray(arr) ? arr : [];
        },
        normalizeMemberRoleValue(role, isLeader) {
            if (Number(isLeader || 0) === 1 || isLeader === true) return 'leader';
            const s = String(role || '').trim();
            if (!s) return 'member';
            if (s === 'leader' || s === '负责人' || s === '1' || s === 'true' || s === 'True') return 'leader';
            if (s === 'member' || s === '成员' || s === '0' || s === 'false' || s === 'False') return 'member';
            return 'member';
        },
        normalizeMembersForUi(rows) {
            const list = Array.isArray(rows) ? rows.map(x => ({ ...(x || {}) })) : [];
            for (const m of list) {
                m.role = this.normalizeMemberRoleValue(m.role, m.is_leader);
                m.is_leader = (m.role === 'leader') ? 1 : 0;
                if (!m.college) m.college = this.getFieldValue(this.createForm, 'extra_info.leader_info.college') || (this.user?.college || '');
                if (m.role === 'leader') {
                    if (!m.student_id) m.student_id = this.user?.identity_number || '';
                    if (!m.name) m.name = this.user?.real_name || '';
                }
            }
            return list;
        },
        validateCollaboratorsInCreateForm() {
            const t = String(this.getFieldValue(this.createForm, 'extra_info.declaration_type') || '').trim();
            if (t !== 'individual' && t !== 'team') return { ok: true, message: '' };
            const key = t === 'individual' ? 'extra_info.collaborators_individual' : 'extra_info.collaborators_team';
            const rows = this.getTableRows(this.createForm, key);
            const limit = t === 'individual' ? 2 : 8;
            if (rows.length < 1) return { ok: false, message: '请完善合作者信息（至少1人）' };
            if (rows.length > limit) return { ok: false, message: `合作者人数超过限制：最多 ${limit} 人` };
            const requiredKeys = ['姓名', '学号', '学历', '专业', '学院', '承担工作'];
            const isEmpty = (v) => v === null || v === undefined || String(v).trim() === '';
            for (let i = 0; i < rows.length; i++) {
                const r = rows[i] || {};
                for (const k of requiredKeys) {
                    if (isEmpty(r[k])) return { ok: false, message: `请完善合作者信息第${i + 1}行：${k}` };
                }
                if (!['本科', '硕士', '博士'].includes(String(r['学历']).trim())) return { ok: false, message: `合作者信息第${i + 1}行：学历请选择本科/硕士/博士` };
            }
            return { ok: true, message: '' };
        },
        removeTableRow(form, key, index) {
            const rows = this.getTableRows(form, key);
            rows.splice(index, 1);
            this.setFieldValue(form, key, rows);
        },
        updateTableCell(form, key, rowIndex, colKey, value) {
            const rows = this.getTableRows(form, key);
            if (!rows[rowIndex] || typeof rows[rowIndex] !== 'object') rows[rowIndex] = {};
            rows[rowIndex][colKey] = value;
            // 如果修改的是学院，则清空该行的专业，以便重新选择
            if (colKey === 'college' && (String(key || '').trim() === 'members' || key.includes('members'))) {
                rows[rowIndex]['major'] = '';
            }
            this.setFieldValue(form, key, rows);
        },
        updateCollaboratorTableCell(form, key, rowIndex, colKey, value) {
            const rows = this.getTableRows(form, key);
            if (!rows[rowIndex] || typeof rows[rowIndex] !== 'object') rows[rowIndex] = {};
            rows[rowIndex][colKey] = value;
            if (colKey === '学历') {
                rows[rowIndex]['学院'] = '';
                rows[rowIndex]['专业'] = '';
            }
            if (colKey === '学院') {
                rows[rowIndex]['专业'] = '';
            }
            this.setFieldValue(form, key, rows);
        },
        setFieldValue(form, key, value) {
            const parts = String(key).split('.');
            if (!parts.length) return;
            let obj = form;
            for (let i = 0; i < parts.length - 1; i++) {
                const p = parts[i];
                if (!obj[p] || typeof obj[p] !== 'object') {
                    obj[p] = {};
                }
                obj = obj[p];
            }
            obj[parts[parts.length - 1]] = value;
        },
        getMajorsByCollege(college) {
            const c = (college || '').trim();
            if (!c) {
                const extra = ['校级管理'];
                return Array.from(new Set([...(this.departments || []), ...extra]));
            }
            const arr = CNMU_COLLEGE_MAJOR[c];
            return Array.isArray(arr) ? arr : [];
        },
        getCollaboratorCollegeOptions(degree) {
            const d = String(degree || '').trim();
            const map = CNMU_DEGREE_COLLEGE_PROGRAMS?.[d];
            if (!map || typeof map !== 'object') return [];
            return Object.keys(map).filter(k => Array.isArray(map[k]) && map[k].length > 0);
        },
        getCollaboratorMajorOptions(row) {
            const d = String(row?.['学历'] || '').trim();
            const college = String(row?.['学院'] || '').trim();
            if (!d || !college) return [];
            const map = CNMU_DEGREE_COLLEGE_PROGRAMS?.[d];
            if (!map || typeof map !== 'object') return [];
            if (d === '本科') return this.getMajorsByCollege(college);
            const list = map[college];
            return Array.isArray(list) ? list : [];
        },
        isOrgRole(role) {
            return ['system_admin', 'school_approver', 'project_admin'].includes(role);
        },
        getField1Label(role) {
            return this.isOrgRole(role) ? '所属部门' : '所属学院';
        },
        getField1Options(role) {
            return this.isOrgRole(role) ? ORG_DEPARTMENTS : CNMU_COLLEGES;
        },
        getIdentityLabel(role) {
            return role === 'student' ? '学号' : '工号';
        },
        getField2Label(role) {
            if (role === 'student') return '专业';
            if (role === 'teacher') return '职称';
            if (role === 'judge') return '职称';
            if (role === 'college_approver') return '职务';
            if (role === 'school_approver') return '职务';
            if (role === 'project_admin') return '职务';
            if (role === 'system_admin') return '职务';
            return '部门/专业';
        },
        getField2Options(role, field1Value) {
            if (role === 'student') return this.getMajorsByCollege(field1Value);
            const arr = ROLE_FIELD2_OPTIONS[role];
            return Array.isArray(arr) ? arr : [];
        },
        rememberIdentity(role, value) {
            try {
                const k = `id_mem_${role || 'unknown'}`;
                if (value === undefined || value === null) return;
                localStorage.setItem(k, String(value));
            } catch (e) {}
        },
        loadIdentityMemory(role) {
            try {
                const k = `id_mem_${role || 'unknown'}`;
                return localStorage.getItem(k) || '';
            } catch (e) { return ''; }
        },
        openCreateDialog() {
            console.log('DEBUG: openCreateDialog called');
            this.isEditing = false;
            this.currentEditingId = null;
            this.showCreateDialog = true;
            this.activeStep = 0;

            // 如果你从“往届项目经验库”点击过“借鉴此项目思路”，则这里预选到创建项目的来源字段
            const legacyInspoId = localStorage.getItem('legacy_inspiration_source_id');
            const borrowCounted = !!legacyInspoId;
            if (legacyInspoId) {
                try { localStorage.removeItem('legacy_inspiration_source_id'); } catch (e) {}
            }
            
            const leaderInfo = {};
            if (this.user?.role === 'student') {
                 leaderInfo.name = this.user.real_name;
                 leaderInfo.id = this.user.identity_number;
                 leaderInfo.college = this.user.college;
            }

            const leaderMember = {
                student_id: leaderInfo.id || '',
                name: leaderInfo.name || '',
                college: leaderInfo.college || '',
                grade: '',
                major: '',
                role: 'leader',
                contact: this.user?.email || ''
            };

            this.createForm = {
                id: undefined, // Explicitly reset ID
                title: '', project_type: 'innovation', level: 'school', year: '2025',
                leader_name: this.user?.real_name || '', advisor_name: '', 
                inspiration_source: legacyInspoId || '', // Initialize inspiration source
                linked_project_id: null,
                // 标记：如果灵感来源来自“借鉴此项目思路”，后端创建项目时不要重复 +1
                borrow_counted: borrowCounted,
                members: (this.user?.role === 'student' && (leaderMember.student_id || leaderMember.name)) ? [leaderMember] : [],
                template_type: 'default',
                extra_info: {
                    leader_info: leaderInfo,
                    advisors: [
                        { name: '', title: '', org: '', guidance_type: '校内导师', research_area: '', phone: '' }
                    ]
                },
                form_config: {
                    show_company_info: true,
                    show_advisor: true,
                    show_team_members: false,
                    show_attachments: true
                }
            };
            console.log('DEBUG: openCreateDialog reset createForm.id to undefined');
            this.fetchJiebangTopicsTree();
            this.ensureCreateFormAdvisors();
        },
        isAdvisorGroup(group) {
            const title = String(group?.title || '').trim();
            return title.includes('指导教师');
        },
        getAdvisorRankLabel(idx) {
            if (idx === 0) return '第一指导教师';
            if (idx === 1) return '第二指导教师';
            if (idx === 2) return '第三指导教师';
            return `第${idx + 1}指导教师`;
        },
        normalizeAdvisorTitle(v) {
            const s = String(v || '').trim();
            if (!s) return '';
            if (s === 'professor') return '教授';
            if (s === 'associate_professor') return '副教授';
            if (s === 'lecturer') return '讲师';
            if (s === 'assistant') return '助教';
            if (s === 'researcher') return '研究员';
            if (s === 'associate_researcher') return '副研究员';
            if (s === 'senior_engineer') return '高级工程师';
            if (s === 'engineer') return '工程师';
            if (s === 'other_senior') return '其他';
            return s;
        },
        getCompetitionTitleById(id) {
            if (!id) return '';
            const comp = this.competitions?.find(c => String(c.id) === String(id));
            return comp ? String(comp.title || '') : '';
        },
        ensureCreateFormAdvisors() {
            if (!this.createForm) this.createForm = {};
            if (!this.createForm.extra_info || typeof this.createForm.extra_info !== 'object') this.createForm.extra_info = {};
            const ei = this.createForm.extra_info;
            if (!Array.isArray(ei.advisors) || ei.advisors.length === 0) {
                const legacyInfo = ei.advisor_info || {};
                const a0 = {
                    name: String(this.createForm.advisor_name || '').trim(),
                    title: this.normalizeAdvisorTitle(legacyInfo.title || ei.advisor_title || ''),
                    org: String(ei.advisor_unit || legacyInfo.dept || '').trim(),
                    guidance_type: '校内导师',
                    research_area: String(ei.advisor_research || '').trim(),
                    phone: String(ei.advisor_phone || legacyInfo.phone || '').trim()
                };
                ei.advisors = [a0];
            } else {
                ei.advisors = ei.advisors.slice(0, 3).map(a => ({
                    name: String(a?.name || '').trim(),
                    title: this.normalizeAdvisorTitle(a?.title || ''),
                    org: String(a?.org || '').trim(),
                    guidance_type: String(a?.guidance_type || '校内导师').trim() || '校内导师',
                    research_area: String(a?.research_area || '').trim(),
                    phone: String(a?.phone || '').trim()
                }));
            }
            if (!this.shouldShowAdvisorGuidanceType) {
                for (const a of ei.advisors) a.guidance_type = '校内导师';
            } else {
                for (const a of ei.advisors) {
                    if (!a.guidance_type) a.guidance_type = '校内导师';
                }
            }
        },
        addAdvisor() {
            this.ensureCreateFormAdvisors();
            const ei = this.createForm.extra_info;
            if (ei.advisors.length >= 3) return;
            ei.advisors.push({ name: '', title: '', org: '', guidance_type: '校内导师', research_area: '', phone: '' });
            this.ensureCreateFormAdvisors();
        },
        removeAdvisor(idx) {
            this.ensureCreateFormAdvisors();
            const ei = this.createForm.extra_info;
            if (ei.advisors.length <= 1) return;
            if (idx <= 0) return;
            ei.advisors.splice(idx, 1);
        },
        advisorTitleLevel(title) {
            const s = String(title || '').trim();
            if (!s) return 0;
            if (s.includes('教授') && !s.includes('副')) return 3;
            if (s.includes('副教授')) return 2;
            if (s.includes('研究员') && !s.includes('副')) return 3;
            if (s.includes('副研究员')) return 2;
            if (s.includes('高级工程师')) return 2;
            if (s.includes('讲师')) return 1;
            if (s.includes('工程师')) return 1;
            if (s.includes('助教')) return 0;
            return 0;
        },
        getMentorValidationCategory() {
            const title = this.getCompetitionTitleById(this.createForm?.competition_id);
            if (title.includes('挑战杯') || title.includes('大挑')) return 'daitiao';
            if (this.createForm?.template_type === 'training') return 'dachuang';
            if (title.includes('大创') || title.includes('创新训练') || title.includes('创业训练') || title.includes('创业实践')) return 'dachuang';
            const ptype = String(this.createForm?.project_type || '');
            if (!this.createForm?.competition_id && ['innovation', 'entrepreneurship_training', 'entrepreneurship_practice'].includes(ptype)) return 'dachuang';
            return 'other';
        },
        isAdvisorComplete(a) {
            const v = (x) => String(x || '').trim();
            if (!v(a?.name)) return false;
            if (!v(a?.title)) return false;
            if (!v(a?.org)) return false;
            if (this.shouldShowAdvisorGuidanceType && !v(a?.guidance_type)) return false;
            if (!v(a?.research_area)) return false;
            if (!v(a?.phone)) return false;
            return true;
        },
        validateAdvisorsInCreateForm() {
            const groups = this.createForm?.form_config?.groups;
            const hasAdvisorGroup = Array.isArray(groups) && groups.some(g => this.isAdvisorGroup(g));
            if (!hasAdvisorGroup) return { ok: true, message: '' };
            this.ensureCreateFormAdvisors();
            const advisors = this.createForm.extra_info.advisors;
            if (!Array.isArray(advisors) || advisors.length < 1) return { ok: false, message: '请至少填写1名指导教师信息' };
            if (advisors.length > 3) return { ok: false, message: '指导教师最多3人' };
            if (!this.isAdvisorComplete(advisors[0])) return { ok: false, message: '第一指导教师信息不完整' };
            for (let i = 1; i < advisors.length; i++) {
                if (!this.isAdvisorComplete(advisors[i])) return { ok: false, message: `请完善指导教师${i + 1}信息或删除该指导教师` };
            }
            const ptype = String(this.createForm?.project_type || '');
            if (ptype === 'entrepreneurship_training' || ptype === 'entrepreneurship_practice') {
                if (advisors.length !== 2) return { ok: false, message: '创业类项目必须填写2位指导教师（校内+校外）' };
                const types = advisors.map(a => String(a?.guidance_type || '').trim());
                if (!types.includes('校内导师') || !types.includes('企业导师')) return { ok: false, message: '创业类项目指导教师类型必须包含校内导师与企业导师各1人' };
            }
            const cat = this.getMentorValidationCategory();
            if (cat === 'daitiao') {
                const ok = advisors.some(a => this.advisorTitleLevel(a.title) >= 2);
                if (!ok) return { ok: false, message: '大挑项目至少1名指导教师职称为副教授或以上' };
            } else if (cat === 'dachuang') {
                const ok = advisors.some(a => this.advisorTitleLevel(a.title) >= 1);
                if (!ok) return { ok: false, message: '大创项目至少1名指导教师职称为讲师或以上' };
            }
            return { ok: true, message: '' };
        },
        validateDynamicRequiredFieldsInCreateForm() {
            const cfg = this.createForm?.form_config;
            const groups = cfg?.groups;
            if (!Array.isArray(groups) || !groups.length) return { ok: true, message: '' };
            for (const group of groups) {
                if (this.isAdvisorGroup(group)) continue;
                if (!this.shouldShow(this.createForm, group)) continue;
                const fields = Array.isArray(group?.fields) ? group.fields : [];
                for (const field of fields) {
                    if (!this.shouldShow(this.createForm, field)) continue;
                    if (!field?.required) continue;
                    const val = this.getFieldValue(this.createForm, field.key);
                    if (val === null || val === undefined) return { ok: false, message: `${field.label || '字段'}为必填项` };
                    if (typeof val === 'string' && val.trim() === '') return { ok: false, message: `${field.label || '字段'}为必填项` };
                    if (Array.isArray(val) && val.length === 0) return { ok: false, message: `${field.label || '字段'}为必填项` };
                    if (typeof val === 'object' && !Array.isArray(val) && Object.keys(val).length === 0) return { ok: false, message: `${field.label || '字段'}为必填项` };
                }
            }
            return { ok: true, message: '' };
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

        getProjectLevelText(level) {
            const s = String(level || '').trim().toLowerCase();
            if (s === 'school' || s === '校级') return '校级';
            if (s === 'provincial' || s === '省级') return '省级';
            if (s === 'national' || s === '国家级') return '国家级';
            return level || '';
        },
        hasPendingUpgradeRequest() {
            return Array.isArray(this.upgradeRequests) && this.upgradeRequests.some(r => r && r.status === 'pending');
        },
        canApplyUpgrade(project) {
            if (!project) return false;
            if (this.hasPendingUpgradeRequest()) return false;
            const s = String(project.status || '');
            if (!['school_approved', 'rated', 'midterm_submitted', 'midterm_approved', 'conclusion_submitted', 'finished'].includes(s)) {
                return false;
            }
            const lv = String(project.level || '').trim().toLowerCase();
            return lv === 'school' || lv === 'provincial' || lv === '校级' || lv === '省级';
        },
        canReviewUpgradeRequests() {
            return ['system_admin', 'project_admin', 'school_approver', 'judge'].includes(this.user?.role);
        },
        openUpgradeDialog(project) {
            const cur = String(project.level || '').trim().toLowerCase();
            const defaultTo = (cur === 'provincial' || cur === '省级') ? 'national' : 'provincial';
            this.upgradeForm = { project_id: project.id, to_level: defaultTo, reason: '' };
            this.showUpgradeDialog = true;
        },
        async loadUpgradeRequests(projectId) {
            this.upgradeRequestsLoading = true;
            try {
                const res = await axios.get(`/api/projects/${projectId}/upgrade-requests`);
                this.upgradeRequests = Array.isArray(res.data) ? res.data : [];
            } catch (e) {
                this.upgradeRequests = [];
            } finally {
                this.upgradeRequestsLoading = false;
            }
        },
        async submitUpgradeRequest() {
            if (!this.upgradeForm?.project_id) return;
            try {
                await axios.post(`/api/projects/${this.upgradeForm.project_id}/upgrade-requests`, {
                    to_level: this.upgradeForm.to_level,
                    reason: this.upgradeForm.reason
                });
                ElementPlus.ElMessage.success('升级申请已提交');
                this.showUpgradeDialog = false;
                await this.loadUpgradeRequests(this.upgradeForm.project_id);
                await this.viewDetails(this.upgradeForm.project_id);
            } catch (e) {
                ElementPlus.ElMessage.error(e.message || '提交失败');
            }
        },
        async reviewUpgradeRequest(id, status) {
            const isReject = status === 'rejected';
            try {
                const { value } = await ElementPlus.ElMessageBox.prompt(
                    isReject ? '请输入驳回原因（必填）' : '请输入审核意见（可选）',
                    isReject ? '驳回升级申请' : '通过升级申请',
                    {
                        confirmButtonText: '确定',
                        cancelButtonText: '取消',
                        inputPlaceholder: isReject ? '驳回原因' : '审核意见',
                        inputValidator: (v) => {
                            if (isReject && !String(v || '').trim()) return '驳回原因不能为空';
                            return true;
                        }
                    }
                );
                await axios.put(`/api/upgrade-requests/${id}/review`, { status, comment: value });
                ElementPlus.ElMessage.success('处理成功');
                if (this.currentProject?.id) {
                    await this.loadUpgradeRequests(this.currentProject.id);
                    await this.viewDetails(this.currentProject.id);
                }
            } catch (e) {
                if (e !== 'cancel') ElementPlus.ElMessage.error(e.message || '处理失败');
            }
        },

        getReviewStageText(v) {
            const s = String(v || '').trim().toLowerCase();
            if (s === 'school' || s === '校赛') return '校赛';
            if (s === 'provincial' || s === '省赛') return '省赛';
            if (s === 'national' || s === '国赛') return '国赛';
            return v || '';
        },
        getReviewResultText(v) {
            const s = String(v || '').trim().toLowerCase();
            if (s === 'approved' || s === '通过') return '通过';
            if (s === 'rejected' || s === '不通过') return '不通过';
            if (s === 'pending' || s === '待评审') return '待评审';
            return v || '';
        },
        getAwardLevelText(v) {
            const s = String(v || '').trim().toLowerCase();
            if (s === 'gold' || s === '金奖') return '金奖';
            if (s === 'silver' || s === '银奖') return '银奖';
            if (s === 'bronze' || s === '铜奖') return '铜奖';
            if (s === 'special' || s === '特等' || s === '特等奖') return '特等奖';
            if (s === 'first' || s === '一等' || s === '一等奖') return '一等奖';
            if (s === 'second' || s === '二等' || s === '二等奖') return '二等奖';
            if (s === 'third' || s === '三等' || s === '三等奖') return '三等奖';
            if (s === 'excellent' || s === '优秀奖' || s === '优秀') return '优秀';
            if (s === '良好') return '良好';
            if (s === '合格') return '合格';
            if (s === '不合格') return '不合格';
            if (s === 'none' || s === '无') return '无';
            return v || '';
        },
        canViewAdminReview() {
            return ['system_admin', 'project_admin', 'college_approver', 'school_approver', 'judge'].includes(this.user?.role);
        },
        canEditAdminField(field) {
            const role = this.user?.role;
            if (!role) return false;
            if (['system_admin', 'project_admin'].includes(role)) return true;
            if (role === 'college_approver') return ['college_review_result', 'department_head_opinion'].includes(field);
            if (role === 'school_approver') return ['review_stage', 'school_review_result', 'provincial_award_level', 'national_award_level', 'research_admin_opinion'].includes(field);
            if (role === 'judge') return ['review_stage', 'college_review_result', 'school_review_result', 'research_admin_opinion', 'department_head_opinion'].includes(field);
            return false;
        },
        initAdminReviewFormFromProject(p) {
            let inferredStage = p?.review_stage || '';
            if (!inferredStage) {
                if (p?.current_level === 'school') inferredStage = 'school';
                else if (p?.current_level === 'provincial') inferredStage = 'provincial';
                else if (p?.current_level === 'national') inferredStage = 'national';
            }
            this.adminReviewForm = {
                review_stage: inferredStage,
                college_review_result: p?.college_review_result || 'pending',
                school_review_result: p?.school_review_result || 'pending',
                provincial_award_level: p?.provincial_award_level || 'none',
                national_award_level: p?.national_award_level || 'none',
                research_admin_opinion: p?.research_admin_opinion || '',
                department_head_opinion: p?.department_head_opinion || ''
            };
        },
        initPnResultFormFromProject(p) {
            this.pnResultForm = {
                provincial_status: p?.provincial_status || '',
                provincial_award_level: p?.provincial_award_level || 'none',
                provincial_certificate_no: p?.provincial_certificate_no || '',
                provincial_advance_national: !!p?.provincial_advance_national,
                provincial_review_comment: p?.provincial_review_comment || '',
                national_status: p?.national_status || '',
                national_award_level: p?.national_award_level || 'none',
                national_certificate_no: p?.national_certificate_no || '',
                national_review_comment: p?.national_review_comment || ''
            };
        },
        async saveAdminReview() {
            if (!this.currentProject?.id) return;
            this.adminReviewSaving = true;
            try {
                await axios.put(`/api/projects/${this.currentProject.id}/admin-review`, { ...this.adminReviewForm });
                ElementPlus.ElMessage.success('保存成功');
                await this.viewDetails(this.currentProject.id);
            } catch (e) {
                ElementPlus.ElMessage.error(e.message || '保存失败');
            } finally {
                this.adminReviewSaving = false;
            }
        },
        async savePnResults() {
            if (!this.currentProject?.id) return;
            this.pnResultSaving = true;
            try {
                if (this.pnResultForm.provincial_award_level && this.pnResultForm.provincial_award_level !== 'none') {
                    this.pnResultForm.provincial_status = '已获奖';
                }
                if (this.pnResultForm.provincial_advance_national && !this.pnResultForm.national_status) {
                    this.pnResultForm.national_status = '未参赛';
                }
                if (this.pnResultForm.national_award_level && this.pnResultForm.national_award_level !== 'none') {
                    this.pnResultForm.national_status = '已获奖';
                }
                await axios.put(`/api/projects/${this.currentProject.id}/competition-results`, { ...this.pnResultForm });
                ElementPlus.ElMessage.success('保存成功');
                await this.viewDetails(this.currentProject.id);
                await this.fetchProjects();
                await this.fetchNotifications();
            } catch (e) {
                ElementPlus.ElMessage.error(e.response?.data?.message || e.response?.data?.error || e.message || '保存失败');
            } finally {
                this.pnResultSaving = false;
            }
        },
        async loadProjectAwards(projectId) {
            this.projectAwardsLoading = true;
            try {
                const res = await axios.get(`/api/projects/${projectId}/awards`);
                this.projectAwards = Array.isArray(res.data) ? res.data : [];
            } catch (e) {
                this.projectAwards = [];
            } finally {
                this.projectAwardsLoading = false;
            }
        },
        async fetchAwards() {
            this.awardsRecordsLoading = true;
            try {
                const res = await axios.get('/api/awards');
                this.awardsRecords = Array.isArray(res.data) ? res.data : [];
            } catch (e) {
                this.awardsRecords = [];
            } finally {
                this.awardsRecordsLoading = false;
            }
        },
        openAwardDialog(row) {
            if (row && row.id) {
                this.awardForm = {
                    id: row.id,
                    project_id: row.project_id,
                    stage: row.stage || 'provincial',
                    award_level: row.award_level || 'none',
                    award_name: row.award_name || '',
                    award_time: row.award_time || '',
                    issuer: row.issuer || ''
                };
            } else {
                this.awardForm = { id: null, project_id: this.currentProject?.id || null, stage: 'provincial', award_level: 'none', award_name: '', award_time: '', issuer: '' };
            }
            this.awardAuto = { name: '', time: '', issuer: '' };
            this.showAwardDialog = true;
        },
        async submitAward() {
            if (!this.awardForm?.project_id) {
                ElementPlus.ElMessage.warning('请选择项目');
                return;
            }
            try {
                if (this.awardForm.id) {
                    await axios.put(`/api/awards/${this.awardForm.id}`, { ...this.awardForm });
                } else {
                    await axios.post(`/api/projects/${this.awardForm.project_id}/awards`, { ...this.awardForm });
                }
                ElementPlus.ElMessage.success('保存成功');
                this.showAwardDialog = false;
                const keepTab = this.detailActiveTab;
                if (this.currentProject?.id) {
                    await this.loadProjectAwards(this.currentProject.id);
                }
                if (this.canManageAwards && this.activeTab === 'award_mgmt') {
                    await this.fetchAwards();
                }
                if (this.currentProject?.id && Number(this.currentProject.id) === Number(this.awardForm.project_id)) {
                    await this.viewDetails(this.awardForm.project_id);
                    this.detailActiveTab = keepTab;
                }
            } catch (e) {
                ElementPlus.ElMessage.error(e.message || '保存失败');
            }
        },
        async deleteAward(id) {
            try {
                await ElementPlus.ElMessageBox.confirm('确认删除该获奖记录？', '提示', { type: 'warning' });
                await axios.delete(`/api/awards/${id}`);
                ElementPlus.ElMessage.success('已删除');
                if (this.currentProject?.id) {
                    await this.loadProjectAwards(this.currentProject.id);
                }
                if (this.canManageAwards && this.activeTab === 'award_mgmt') {
                    await this.fetchAwards();
                }
            } catch (e) {}
        },

        async maybePromptLinkDachuang(comp) {
            if (this.user?.role !== 'student') return;
            const title = String(comp?.title || '');
            const allow = title.includes('大创创新训练') || title.includes('大创创业训练') || title.includes('大创创业实践') || title.includes('大学生创新训练计划') || title.includes('大学生创新创业训练计划');
            if (!allow) return;
            try {
                const res = await axios.get('/api/my/dachuang-projects');
                const list = Array.isArray(res.data) ? res.data : [];
                if (!list.length) return;
                this.dachuangCandidates = list;
                this.dachuangLinkSelected = list[0]?.id || null;
                this.showLinkDachuangDialog = true;
            } catch (e) {}
        },
        skipLinkDachuang() {
            this.showLinkDachuangDialog = false;
            this.dachuangCandidates = [];
            this.dachuangLinkSelected = null;
        },
        async confirmLinkDachuang() {
            const id = this.dachuangLinkSelected;
            if (!id) {
                ElementPlus.ElMessage.warning('请选择一个大创项目');
                return;
            }
            this.createForm.linked_project_id = id;
            this.showLinkDachuangDialog = false;
            try {
                const res = await axios.get(`/api/projects/${id}`);
                const p = res.data || {};
                const src = p.extra_info || {};
                if (!this.createForm.extra_info) this.createForm.extra_info = {};
                if (!this.createForm.extra_info.attachments) this.createForm.extra_info.attachments = {};
                if (this.createForm.extra_info.expected_outcomes == null && src.expected_outcomes != null) {
                    this.createForm.extra_info.expected_outcomes = src.expected_outcomes;
                }
                if (this.createForm.extra_info.innovation_points == null && src.innovation_points != null) {
                    this.createForm.extra_info.innovation_points = src.innovation_points;
                }
                if (src.attachments && typeof src.attachments === 'object') {
                    for (const k of Object.keys(src.attachments)) {
                        if (this.createForm.extra_info.attachments[k] == null) {
                            this.createForm.extra_info.attachments[k] = src.attachments[k];
                        }
                    }
                }
                this.createForm.extra_info.reused_from_project_id = id;
                ElementPlus.ElMessage.success('已关联并复用成果数据');
            } catch (e) {
                ElementPlus.ElMessage.success('已关联大创项目');
            }
        },
        
        async submitProject() {
            if (this.submitting) return; // Prevent double submission
            console.log('DEBUG: submitProject called');
            console.log('DEBUG: isEditing:', this.isEditing);
            console.log('DEBUG: createForm.id:', this.createForm.id);
            console.log('DEBUG: createForm full:', JSON.parse(JSON.stringify(this.createForm)));

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

            this.ensureCreateFormAdvisors();
            const advisorCheck = this.validateAdvisorsInCreateForm();
            if (!advisorCheck.ok) {
                ElementPlus.ElMessage.warning(advisorCheck.message);
                return;
            }
            const collaboratorsCheck = this.validateCollaboratorsInCreateForm();
            if (!collaboratorsCheck.ok) {
                ElementPlus.ElMessage.warning(collaboratorsCheck.message);
                return;
            }
            const dynCheck = this.validateDynamicRequiredFieldsInCreateForm();
            if (!dynCheck.ok) {
                ElementPlus.ElMessage.warning(dynCheck.message);
                return;
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
                if (!payload.extra_info || typeof payload.extra_info !== 'object') payload.extra_info = {};
                if (!Array.isArray(payload.extra_info.advisors)) payload.extra_info.advisors = [];
                if (payload.extra_info.advisors.length) {
                    const a0 = payload.extra_info.advisors[0] || {};
                    payload.advisor_name = String(a0.name || '').trim();
                    payload.extra_info.advisor_title = String(a0.title || '').trim();
                    payload.extra_info.advisor_unit = String(a0.org || '').trim();
                    payload.extra_info.advisor_research = String(a0.research_area || '').trim();
                    payload.extra_info.advisor_phone = String(a0.phone || '').trim();
                    payload.extra_info.advisor_info = {
                        dept: String(a0.org || '').trim(),
                        title: String(a0.title || '').trim(),
                        phone: String(a0.phone || '').trim(),
                        email: String(payload.extra_info?.advisor_info?.email || '').trim()
                    };
                }
                if (payload.template_type === 'startup' && Array.isArray(payload.members)) {
                    payload.members = payload.members.slice(1);
                }

                // --- STRICT ID ENFORCEMENT START ---
                // We rely exclusively on currentEditingId to determine the target ID.
                // This neutralizes any "Ghost IDs" (6, 7, 8...) that might appear in createForm.id
                
                if (this.currentEditingId) {
                    payload.id = this.currentEditingId;
                    this.createForm.id = this.currentEditingId; 
                    this.isEditing = true;
                } else {
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
                this.createForm = { id: undefined, title: '', project_type: 'innovation', members: [], linked_project_id: null }; 
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
                    ElementPlus.ElMessage.error(error.response?.data?.error || error.response?.data?.message || '操作失败');
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
                const byComp = new Map();
                for (const p of (Array.isArray(this.projects) ? this.projects : [])) {
                    const cid = Number(p?.competition_id);
                    const pid = Number(p?.id);
                    if (isNaN(cid) || cid <= 0) continue;
                    if (isNaN(pid) || pid <= 0) continue;
                    if (!byComp.has(cid)) byComp.set(cid, p);
                }

                const uid = Number(this.user?.id);
                this.competitions = (Array.isArray(this.competitions) ? this.competitions : []).map(c => {
                    if (!c) return c;
                    const cid = Number(c.id);
                    const mapped = byComp.get(cid);
                    const pid0 = Number(c.project_id);

                    if (c.is_registered) {
                        if (isNaN(pid0) || pid0 <= 0 || !validIds.has(pid0)) {
                            return { ...c, is_registered: false, project_id: null, project_status: null, is_leader: false };
                        }
                        return c;
                    }

                    if (mapped) {
                        const isLeader = !isNaN(uid) && uid > 0 && Number(mapped.created_by) === uid;
                        return { ...c, is_registered: true, project_id: mapped.id, project_status: mapped.status, is_leader: isLeader };
                    }

                    return c;
                });
            } catch(e) { console.error('DEBUG: sync error', e); }
        },

        // --- Competition Management ---
        openCompDialog(comp) {
            this.showCompDialog = true;
            this.selectedPreset = '';
            if (comp) {
                this.isEditingComp = true;
                this.compForm = { ...comp };
                // Ensure form_config exists
                if (!this.compForm.form_config) {
                    this.compForm.form_config = {
                        groups: []
                    };
                } else if (typeof this.compForm.form_config === 'string') {
                    try {
                        this.compForm.form_config = JSON.parse(this.compForm.form_config);
                    } catch(e) {
                        this.compForm.form_config = {
                            groups: []
                        };
                    }
                }
                // Ensure new fields exist for legacy data
            } else {
                this.isEditingComp = false;
                this.compForm = { 
                    title: '', level: 'School', organizer: '', registration_start: '', registration_end: '', status: 'active', 
                    system_type: '', competition_level: '', national_organizer: '', school_organizer: '',
                    template_type: 'default',
                    form_config: {
                        groups: []
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
                this.compForm.level = preset.data.level || 'School';
                this.compForm.template_type = preset.data.template_type || 'default';
                this.compForm.organizer = preset.data.organizer || '';
                
                this.compForm.system_type = preset.data.system_type || '';
                this.compForm.competition_level = preset.data.competition_level || '';
                this.compForm.national_organizer = preset.data.national_organizer || '';
                this.compForm.school_organizer = preset.data.school_organizer || '';
                
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
                ElementPlus.ElMessage.error(e.message || '操作失败'); 
            }
        },
        async deleteCompetition(id) {
            try {
                await ElementPlus.ElMessageBox.confirm('确定删除该赛事吗？', '提示', { type: 'warning' });
                await axios.delete(`/api/competitions/${id}`);
                ElementPlus.ElMessage.success('删除成功');
                this.fetchCompetitions();
            } catch(e) {
                if (e !== 'cancel') ElementPlus.ElMessage.error(e.message || '删除失败');
            }
        },
        async applyCompetition(comp) {
            console.log('DEBUG: applyCompetition called with:', comp);
            this.openCreateDialog();
            this.createForm.competition_id = comp.id;
            // Explicitly ensure ID is undefined for new application
            this.createForm.id = undefined;
            const inferredTpl = this.inferCompetitionTemplateType(comp);
            this.createForm.template_type = inferredTpl || comp.template_type || 'default';
            this.createForm.title = comp.title + ' - 参赛项目';
            
            if (comp.form_config) {
                try {
                    this.createForm.form_config = (typeof comp.form_config === 'string') ? JSON.parse(comp.form_config) : comp.form_config;
                } catch(e) {
                    console.error("Error parsing form_config", e);
                }
            }

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
                    attachments: {},
                    advisors: [
                        { name: '', title: '', org: '', guidance_type: '校内导师', research_area: '', phone: '' }
                    ]
                };
            } else {
                this.createForm.project_type = this.inferProjectTypeFromCompetition(comp);
            }
            this.ensureCreateFormAdvisors();
            await this.maybePromptLinkDachuang(comp);
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
                
                try {
                    const ei = this.currentProject?.extra_info || {};
                    this.methodologySummary = ei.methodology_summary || '';
                    if (ei.methodology_sections && typeof ei.methodology_sections === 'object') {
                        this.methodologySections = { bg: '', process: '', innovation: '', effect: '', norm: '', ...ei.methodology_sections };
                    } else {
                        this.methodologySections = { bg: '', process: '', innovation: '', effect: '', norm: '' };
                    }
                    if (ei.methodology_attachments && typeof ei.methodology_attachments === 'object') {
                        this.processFiles.methodology = { route_map: null, photo: null, attachment: null, compliance_material: null, ...ei.methodology_attachments };
                    } else {
                        this.processFiles.methodology = { route_map: null, photo: null, attachment: null, compliance_material: null };
                    }
                    this.collegeRecForm.defense_score = this.currentProject?.college_defense_score ?? null;
                    this.collegeRecForm.recommend_rank = this.currentProject?.college_recommend_rank ?? null;
                    this.collegeRecForm.is_key_support = !!this.currentProject?.is_key_support;
                } catch (e) {
                    this.methodologySummary = '';
                    this.processFiles.methodology = { route_map: null, photo: null, attachment: null, compliance_material: null };
                    this.methodologySections = { bg: '', process: '', innovation: '', effect: '', norm: '' };
                    this.collegeRecForm.defense_score = null;
                    this.collegeRecForm.recommend_rank = null;
                    this.collegeRecForm.is_key_support = false;
                }

                let tpl = 'default';
                let comp = null;
                if (this.currentProject.competition_id) {
                    const compId = Number(this.currentProject.competition_id);
                    comp = this.competitions.find(c => Number(c.id) === compId);
                    if (!comp) {
                        try {
                            const compsRes = await axios.get('/api/competitions');
                            this.competitions = compsRes.data;
                            comp = this.competitions.find(c => Number(c.id) === compId);
                        } catch(e) {}
                    }
                    const inferredTpl = this.inferCompetitionTemplateType(comp);
                    if (inferredTpl) tpl = inferredTpl;
                    else if (comp && comp.template_type) tpl = comp.template_type;
                }
                if (comp && comp.form_config) {
                    try {
                        const fc = (typeof comp.form_config === 'string') ? JSON.parse(comp.form_config) : comp.form_config;
                        this.currentProject.form_config = fc;
                    } catch (e) {
                        this.currentProject.form_config = { groups: [] };
                    }
                }
                const info = this.currentProject?.extra_info || {};
                if (tpl === 'default' && (info.company_info || info.leader_info || info.attachments)) {
                    tpl = 'startup';
                }
                this.currentProject.template_type = tpl;
                if (tpl === 'training') {
                    await this.loadUpgradeRequests(cleanId);
                } else {
                    this.upgradeRequests = [];
                }
                if (this.canViewAdminReview()) {
                    this.initAdminReviewFormFromProject(this.currentProject);
                    await this.loadProjectAwards(cleanId);
                } else {
                    this.projectAwards = [];
                }
                if (this.user?.role === 'school_approver') {
                    this.initPnResultFormFromProject(this.currentProject);
                }

                await this.fetchProjectProcess(cleanId);

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

            if (!this.auditFeedback) {
                ElementPlus.ElMessage.warning('审批意见为必填项');
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
            this.reviewForm = { 
                score: 80, 
                comment: '', 
                criteria_scores: { score_innovation: 8, score_feasibility: 8, score_value: 8 } 
            };
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
                
                let payload = { ...this.reviewForm };
                if (this.currentProject.project_type === 'challenge_cup') {
                    payload.score = Math.round((payload.criteria_scores.score_innovation + payload.criteria_scores.score_feasibility + payload.criteria_scores.score_value) * 3.33);
                }
                
                const url = `/api/projects/${parseInt(this.currentProject.id, 10)}/review`;
                console.log('Submitting review to:', url, payload);

                await axios.post(url, payload);
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

        // New Review Tasks and Assignment methods
        async fetchMyReviewTasks() {
            if (!['judge', 'teacher', 'college_approver', 'school_approver'].includes(this.user?.role)) return;
            this.loadingReviews = true;
            try {
                const res = await axios.get('/api/reviews/tasks');
                const payload = res ? res.data : null;
                if (payload && payload.code && payload.code !== 200) {
                    this.myReviewTasks = [];
                    ElementPlus.ElMessage.error(payload.message || '获取评审任务失败');
                    return;
                }
                const list = Array.isArray(payload) ? payload : (payload && Array.isArray(payload.data) ? payload.data : []);
                this.myReviewTasks = list;
            } catch(e) {
                console.error('Failed to fetch review tasks', e);
                this.myReviewTasks = [];
                ElementPlus.ElMessage.error(e.response?.data?.message || e.response?.data?.error || '获取评审任务失败');
            } finally {
                this.loadingReviews = false;
            }
        },
        openTaskReviewDialog(task) {
            this.currentTask = task;
            const details = task && task.score_details ? task.score_details : {};
            const reasons = {};
            const scores = task && task.criteria_scores ? task.criteria_scores : {};
            Object.keys(scores || {}).forEach(k => {
                const v = details && details[k] ? details[k] : null;
                reasons[k] = typeof v === 'string' ? v : (v && typeof v.reason === 'string' ? v.reason : '');
            });
            this.taskReviewForm = {
                criteria_scores: { ...scores },
                score_reasons: reasons,
                comments: task.comments || '',
                is_recommended: task.is_recommended === 1,
                declaration: task.declaration === 1
            };
            this.showTaskReviewDialog = true;
        },
        async submitTaskReview(status) {
            const isTemporary = status === true || status === 'draft' || status === 'temporary';
            const isFinal = status === false || status === 'completed' || status === 'final';
            const is_temporary = isFinal ? false : isTemporary;
            if (!is_temporary && !this.taskReviewForm.declaration) {
                ElementPlus.ElMessage.warning('必须勾选回避声明');
                return;
            }
            if (!is_temporary && !this.taskReviewForm.comments) {
                ElementPlus.ElMessage.warning('综合评审意见为必填项');
                return;
            }
            this.submitting = true;
            try {
                await axios.post(`/api/reviews/tasks/${this.currentTask.id}`, {
                    is_temporary,
                    comments: this.taskReviewForm.comments,
                    criteria_scores: this.taskReviewForm.criteria_scores,
                    score_reasons: this.taskReviewForm.score_reasons,
                    is_recommended: this.taskReviewForm.is_recommended,
                    declaration: this.taskReviewForm.declaration
                });
                ElementPlus.ElMessage.success(is_temporary ? '暂存成功' : '提交成功');
                this.showTaskReviewDialog = false;
                this.fetchMyReviewTasks();
            } catch(e) {
                ElementPlus.ElMessage.error(e.response?.data?.message || e.response?.data?.error || e.message || '保存失败');
            } finally {
                this.submitting = false;
            }
        },
        async openAssignDialog(project) {
            this.currentProject = project;
            const userRole = this.user?.role;
            const defaultLevel = userRole === 'school_approver' ? 'school' : 'college';
            this.assignForm = { judge_ids: [], review_level: defaultLevel };
            
            try {
                const res = await axios.get('/api/users');
                let judges = (res.data || []).filter(u => ['teacher', 'judge', 'college_approver', 'school_approver'].includes(u.role));
                
                // 院赛级别：显示项目所属学院或包含关键名称的评委
                if (defaultLevel === 'college' && project.college) {
                    const cleanName = project.college.replace(/（.*）|\(.*\)/g, '').trim();
                    judges = judges.filter(u => {
                        if (!u.college) return false;
                        const uCollege = String(u.college);
                        return uCollege === project.college || uCollege.includes(cleanName) || uCollege.includes('计算机');
                    });
                } else if (defaultLevel === 'school') {
                    // 校赛级别：显示所有评委，但校级评委（学院为空）排在前面
                    judges.sort((a, b) => {
                        if (!a.college && b.college) return -1;
                        if (a.college && !b.college) return 1;
                        return 0;
                    });
                }
                
                this.availableJudges = judges;
                this.showAssignDialog = true;
            } catch(e) {
                ElementPlus.ElMessage.error('无法获取评委列表');
            }
        },
        async submitAssignReviewers() {
            if (this.assignForm.judge_ids.length === 0) {
                ElementPlus.ElMessage.warning('请选择至少一名评委');
                return;
            }
            this.submitting = true;
            try {
                await axios.post('/api/reviews/assign', {
                    project_id: this.currentProject.id,
                    judge_ids: this.assignForm.judge_ids,
                    review_level: this.assignForm.review_level
                });
                ElementPlus.ElMessage.success('分配成功');
                this.showAssignDialog = false;
                this.fetchProjects();
            } catch(e) {
                ElementPlus.ElMessage.error(e.response?.data?.error || '分配失败');
            } finally {
                this.submitting = false;
            }
        },
        async calcReviewRank() {
            this.calculatingRank = true;
            try {
                // Determine which level to calculate based on user role
                const level = this.user?.role === 'school_approver' ? 'school' : 'college';
                // For simplicity, just pick the first competition ID if filtering by competition, or let backend handle all active competitions.
                // Assuming backend can handle it without competition_id or we pass the current active one.
                await axios.post('/api/reviews/calc_rank', { review_level: level });
                ElementPlus.ElMessage.success('计算完成');
                this.fetchProjects();
            } catch(e) {
                ElementPlus.ElMessage.error(e.response?.data?.error || '计算失败');
            } finally {
                this.calculatingRank = false;
            }
        },
        async recommendProject(project, nextLevel) {
            try {
                await axios.post('/api/reviews/recommend', {
                    project_id: project.id,
                    next_level: nextLevel
                });
                ElementPlus.ElMessage.success('推荐成功');
                this.fetchProjects();
            } catch(e) {
                ElementPlus.ElMessage.error(e.response?.data?.error || '推荐失败');
            }
        },
        async bootstrapReviewsForProject1() {
            this.bootstrappingReviews = true;
            try {
                // 默认初始化 ID 18 或 ID 1，后端已增加自动寻址第一个可用项目的逻辑
                const res = await axios.post('/api/reviews/test/bootstrap', { project_id: 18, review_level: 'college' });
                const actualId = res.data?.project_id || 18;
                ElementPlus.ElMessage.success(`已初始化评审任务 (项目ID: ${actualId})`);
                await this.fetchProjects();
                await this.fetchMyReviewTasks();
            } catch (e) {
                ElementPlus.ElMessage.error(e.response?.data?.message || e.response?.data?.error || '初始化失败');
            } finally {
                this.bootstrappingReviews = false;
            }
        },
        async copyText(text) {
            try {
                await navigator.clipboard.writeText(text);
                ElementPlus.ElMessage.success('已复制');
            } catch (e) {
                ElementPlus.ElMessage.warning('复制失败，请手动复制');
            }
        },

        // File Upload Helpers
        handleFileUpload(event, path) {
            const target = event.target;
            const file = target.files[0];
            if (!file) return;

            if (file.size > 25 * 1024 * 1024) { // Max 25MB as per requirement (video)
                ElementPlus.ElMessage.warning('文件大小不能超过25MB');
                target.value = '';
                return;
            }

            const formData = new FormData();
            formData.append('file', file);

            axios.post('/api/common/upload', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            }).then(res => {
                this.setFieldValue(this.createForm, path, res.data.url);
                
                // 同步到详情弹窗的 currentProject（如果正在查看同一项目）
                if (this.showDetailDialog && this.currentProject && this.currentProject.id === this.createForm.id) {
                    this.setFieldValue(this.currentProject, path, res.data.url);
                }
                
                ElementPlus.ElMessage.success('上传成功');
                target.value = '';
                
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
                console.error("Upload Error:", err, err.response ? err.response.data : "");
                ElementPlus.ElMessage.error('上传失败: ' + (err.response?.data?.error || err.message));
                target.value = '';
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

        async fetchBorrowedOptions() {
            if (this.user?.role !== 'student') return;
            try {
                const res = await axios.get('/api/legacy', { params: { only_borrowed: '1' } });
                const borrowed = res.data.map(p => ({ label: p.title, value: p.id }));
                const field = FIELD_LIBRARY.find(f => f.key === 'extra_info.borrowed_citations');
                if (field) field.options = borrowed;
            } catch (e) { console.error(e); }
        },
        async editProject(row) {
            this.loading = true;
            try {
                await this.fetchBorrowedOptions(); // 加载借鉴过的项目作为引用选项
                console.log('DEBUG: editProject called with:', JSON.parse(JSON.stringify(row)));
                if (!row || row.id === undefined || row.id === null || isNaN(Number(row.id)) || Number(row.id) <= 0) {
                    ElementPlus.ElMessage.warning('项目ID缺失或无效，请刷新列表后重试');
                    await this.fetchProjects();
                    return;
                }

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
                let form_config = { groups: [] };
                let visibility = { show_company_info: false, show_advisor: true, show_team_members: false, show_attachments: true };
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
                        if (comp.form_config) {
                            try {
                                const cfg = typeof comp.form_config === 'string' ? JSON.parse(comp.form_config) : comp.form_config;
                                form_config = cfg && typeof cfg === 'object' ? cfg : { groups: [] };
                                visibility = {
                                    show_company_info: cfg.show_company_info ?? false,
                                    show_advisor: cfg.show_advisor ?? true,
                                    show_team_members: cfg.show_team_members ?? false,
                                    show_attachments: cfg.show_attachments ?? true
                                };
                            } catch(e) {
                                form_config = { groups: [] };
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
                if (!form_config || typeof form_config !== 'object') form_config = { groups: [] };
                if (!Array.isArray(form_config.groups)) form_config.groups = [];
                form_config.show_company_info = visibility.show_company_info;
                form_config.show_advisor = visibility.show_advisor;
                form_config.show_team_members = visibility.show_team_members;
                form_config.show_attachments = visibility.show_attachments;
                
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
                    
                    members: (template_type === 'startup') ? project.members.filter(m => !m.is_leader) : (project.members || [])
                };
                if (!this.createForm.extra_info) this.createForm.extra_info = {};
                if (!this.createForm.extra_info.attachments) this.createForm.extra_info.attachments = {};
                this.ensureCreateFormAdvisors();
                if (template_type !== 'startup' && Array.isArray(this.createForm.members)) {
                    this.createForm.members = this.normalizeMembersForUi(this.createForm.members);
                }
                
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
            this.createUserForm = {
                username: '',
                real_name: '',
                role: '',
                college: this.user?.role === 'college_approver' ? (this.user?.college || '') : '',
                department: '',
                identity_number: '',
                teaching_office: '',
                research_area: '',
                password: ''
            };
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
            if (this.editUserForm.identity_number === undefined || this.editUserForm.identity_number === null) this.editUserForm.identity_number = '';
            if (this.editUserForm.teaching_office === undefined || this.editUserForm.teaching_office === null) this.editUserForm.teaching_office = '';
            if (this.editUserForm.research_area === undefined || this.editUserForm.research_area === null) this.editUserForm.research_area = '';
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

// 3. 往届项目经验库组件
const LegacyLibrary = {
    template: `
    <div class="legacy-library-container">
        <el-tabs v-model="activeTab" class="mb-4">
            <el-tab-pane label="经验库" name="library">
                <el-card shadow="hover" class="mb-4">
                    <template #header>
                        <div style="display: flex; justify-content: space-between; align-items: center; gap: 12px;">
                            <span style="font-weight: bold; font-size: 18px;"><el-icon><Collection /></el-icon> 往届项目经验库</span>
                            <div style="display: flex; gap: 10px; flex-wrap: wrap; justify-content: flex-end;">
                                <el-input v-model="filters.keyword" placeholder="项目名称/方法论/避坑指南" style="width: 260px;" clearable @clear="fetchLegacy" @keyup.enter="fetchLegacy">
                                    <template #prefix><el-icon><Search /></el-icon></template>
                                </el-input>
                                <el-select v-model="filters.competition_type" @change="fetchLegacy" style="width: 140px;">
                                    <el-option v-for="opt in competitionTypeOptions" :key="opt.value" :label="opt.label" :value="opt.value"></el-option>
                                </el-select>
                                <el-select v-model="filters.category" @change="fetchLegacy" style="width: 120px;">
                                    <el-option label="全部类别" value="all"></el-option>
                                    <el-option label="创新类" value="innovation"></el-option>
                                    <el-option label="创业类" value="entrepreneurship"></el-option>
                                </el-select>
                                <el-select v-model="filters.award_level" @change="fetchLegacy" style="width: 120px;">
                                    <el-option v-for="opt in awardLevelOptions" :key="opt.value" :label="opt.label" :value="opt.value"></el-option>
                                </el-select>
                                <el-button type="primary" @click="fetchLegacy">搜索</el-button>
                            </div>
                        </div>
                    </template>

                    <el-table :data="legacyProjects" v-loading="loading" style="width: 100%">
                        <el-table-column prop="title" label="项目名称" min-width="260">
                            <template #default="scope">
                                <div style="display:flex; align-items:center; gap:8px; flex-wrap: wrap;">
                                    <span style="font-weight: 500;">{{ scope.row.title }}</span>
                                    <el-tag size="small" effect="plain">{{ getCompetitionTypeLabel(scope.row.project_type) }}</el-tag>
                                    <el-tag size="small" :type="scope.row.project_category === 'innovation' ? 'success' : 'warning'">
                                        {{ scope.row.project_category === 'innovation' ? '创新类' : '创业类' }}
                                    </el-tag>
                                </div>
                            </template>
                        </el-table-column>
                        <el-table-column label="获奖级别" width="140">
                            <template #default="scope">
                                <el-tag size="small" effect="plain">{{ scope.row.award_level_label || getAwardLevelText(scope.row.award_level) || '—' }}</el-tag>
                            </template>
                        </el-table-column>
                        <el-table-column label="借鉴次数" width="110" align="center">
                            <template #default="scope">
                                <span style="font-weight: bold; color: #409eff;">{{ scope.row.borrowed_count }}</span>
                            </template>
                        </el-table-column>
                        <el-table-column label="收录时间" width="180">
                            <template #default="scope">
                                <span>{{ scope.row.created_at }}</span>
                            </template>
                        </el-table-column>
                        <el-table-column label="操作" width="200" fixed="right">
                            <template #default="scope">
                                <el-button size="small" @click="openDetail(scope.row)">查看详情</el-button>
                                <el-button v-if="user?.role === 'student'" type="primary" size="small" :disabled="scope.row.is_borrowed" @click="openBorrow(scope.row)">
                                    {{ scope.row.is_borrowed ? '已借鉴' : '借鉴' }}
                                </el-button>
                            </template>
                        </el-table-column>
                    </el-table>
                </el-card>
            </el-tab-pane>

            <el-tab-pane v-if="canManage" label="待审核" name="pending">
                <el-card shadow="hover">
                    <template #header>
                        <div style="display:flex; justify-content: space-between; align-items:center;">
                            <span style="font-weight: bold;">待审核入库</span>
                            <el-button size="small" @click="fetchPending">刷新</el-button>
                        </div>
                    </template>
                    <el-table :data="pendingList" v-loading="pendingLoading" style="width:100%">
                        <el-table-column prop="title" label="项目名称" min-width="260"></el-table-column>
                        <el-table-column label="类别" width="120">
                            <template #default="scope">
                                <el-tag size="small" :type="scope.row.project_category === 'innovation' ? 'success' : 'warning'">
                                    {{ scope.row.project_category === 'innovation' ? '创新类' : '创业类' }}
                                </el-tag>
                            </template>
                        </el-table-column>
                        <el-table-column label="获奖级别" width="140">
                            <template #default="scope">
                                <el-tag size="small" effect="plain">{{ scope.row.award_level_label || getAwardLevelText(scope.row.award_level) || '—' }}</el-tag>
                            </template>
                        </el-table-column>
                        <el-table-column label="操作" width="240" fixed="right">
                            <template #default="scope">
                                <el-button size="small" @click="openDetail(scope.row)">查看</el-button>
                                <el-button type="success" size="small" @click="openReview(scope.row, 'approve')">通过</el-button>
                                <el-button type="danger" size="small" @click="openReview(scope.row, 'reject')">驳回</el-button>
                            </template>
                        </el-table-column>
                    </el-table>
                </el-card>
            </el-tab-pane>
        </el-tabs>

        <el-dialog v-model="showDetail" title="经验库详情" width="900px" top="5vh">
            <el-skeleton v-if="detailLoading" :rows="8" animated></el-skeleton>
            <div v-else-if="currentLegacy">
                <el-descriptions title="基础信息" :column="2" border>
                    <el-descriptions-item label="项目名称" :span="2">{{ currentLegacy.title }}</el-descriptions-item>
                    <el-descriptions-item label="类别">{{ currentLegacy.project_category === 'innovation' ? '创新类' : '创业类' }}</el-descriptions-item>
                    <el-descriptions-item label="竞赛类型">{{ getCompetitionTypeLabel(currentLegacy.project_type) }}</el-descriptions-item>
                    <el-descriptions-item label="获奖级别">{{ currentLegacy.award_level_label || getAwardLevelText(currentLegacy.award_level) || '—' }}</el-descriptions-item>
                    <el-descriptions-item label="借鉴次数">{{ currentLegacy.borrowed_count }}</el-descriptions-item>
                </el-descriptions>

                <el-divider content-position="left">团队与指导教师（已脱敏）</el-divider>
                <div v-if="currentLegacy.base_info">
                    <div style="margin-bottom: 8px;">指导教师：{{ currentLegacy.base_info.advisor_name || '—' }}</div>
                    <el-table :data="currentLegacy.base_info.team || []" size="small" border style="width: 100%">
                        <el-table-column prop="role" label="角色" width="120"></el-table-column>
                        <el-table-column prop="name" label="成员（脱敏）"></el-table-column>
                    </el-table>
                </div>

                <el-divider content-position="left">获奖信息</el-divider>
                <el-table :data="currentLegacy.awards || []" size="small" border style="width: 100%">
                    <el-table-column prop="stage" label="阶段" width="120"></el-table-column>
                    <el-table-column prop="award_level_label" label="等级" width="120"></el-table-column>
                    <el-table-column prop="award_name" label="奖项名称"></el-table-column>
                    <el-table-column prop="award_time" label="时间" width="120"></el-table-column>
                    <el-table-column prop="issuer" label="颁奖单位" width="160"></el-table-column>
                </el-table>

                <el-divider content-position="left">成果与经验（已脱敏）</el-divider>
                    <el-descriptions :column="1" border>
                        <el-descriptions-item label="项目摘要">{{ currentLegacy.project_summary || '—' }}</el-descriptions-item>
                        <el-descriptions-item label="方法论总结">{{ currentLegacy.methodology_summary || '—' }}</el-descriptions-item>
                        <el-descriptions-item v-if="currentLegacy.project_category === 'innovation'" label="专家评语（脱敏）">{{ currentLegacy.expert_comments || '—' }}</el-descriptions-item>
                        <el-descriptions-item v-if="currentLegacy.project_category !== 'innovation'" label="避坑指南">{{ currentLegacy.pitfalls || '—' }}</el-descriptions-item>
                    </el-descriptions>

                <el-divider content-position="left">脱敏附件</el-divider>
                <el-table :data="currentLegacy.files || []" size="small" border style="width: 100%">
                    <el-table-column prop="file_type" label="类型" width="140"></el-table-column>
                    <el-table-column prop="name" label="文件名"></el-table-column>
                    <el-table-column label="操作" width="120">
                        <template #default="scope">
                            <el-button size="small" @click="downloadFile(scope.row)">下载</el-button>
                        </template>
                    </el-table-column>
                </el-table>
            </div>
            <template #footer>
                <el-button @click="showDetail=false">关闭</el-button>
                <el-button v-if="user?.role==='teacher'" type="warning" @click="openPitfall">补充避坑指南</el-button>
                <el-button v-if="user?.role==='student' && currentLegacy && !currentLegacy.is_borrowed" type="primary" @click="openBorrow(currentLegacy)">借鉴</el-button>
            </template>
        </el-dialog>

        <el-dialog v-model="showBorrowDialog" title="借鉴理由" width="600px">
            <el-input v-model="borrowReason" type="textarea" :rows="4" placeholder="可选：填写借鉴理由（将用于数据统计与申报关联）"></el-input>
            <template #footer>
                <el-button @click="showBorrowDialog=false">取消</el-button>
                <el-button type="primary" @click="submitBorrow">确认借鉴</el-button>
            </template>
        </el-dialog>

        <el-dialog v-model="showPitfallDialog" title="补充避坑指南（需审核）" width="700px">
            <el-input v-model="pitfallContent" type="textarea" :rows="6" placeholder="请提交脱敏后的避坑指南"></el-input>
            <template #footer>
                <el-button @click="showPitfallDialog=false">取消</el-button>
                <el-button type="primary" @click="submitPitfall">提交审核</el-button>
            </template>
        </el-dialog>

        <el-dialog v-model="showReviewDialog" title="入库审核" width="600px">
            <div v-if="reviewTarget">
                <div style="margin-bottom: 8px;">项目：{{ reviewTarget.title }}</div>
                <el-radio-group v-model="reviewAction" style="margin-bottom: 12px;">
                    <el-radio label="approve">通过</el-radio>
                    <el-radio label="reject">驳回</el-radio>
                </el-radio-group>
                <el-checkbox v-model="reviewPublic" v-if="reviewAction==='approve'">通过后公开展示</el-checkbox>
                <el-input v-if="reviewAction==='reject'" v-model="reviewRejectReason" type="textarea" :rows="4" placeholder="请填写驳回原因"></el-input>
            </div>
            <template #footer>
                <el-button @click="showReviewDialog=false">取消</el-button>
                <el-button type="primary" :loading="reviewSubmitting" @click="submitReview">确认</el-button>
            </template>
        </el-dialog>
    </div>
    `,
    props: ['user'],
    data() {
        return {
            loading: false,
            legacyProjects: [],
            activeTab: 'library',
            filters: {
                keyword: '',
                category: 'all',
                competition_type: 'all',
                award_level: 'all'
            },
            showDetail: false,
            detailLoading: false,
            currentLegacy: null,
            showBorrowDialog: false,
            borrowReason: '',
            borrowTarget: null,
            showPitfallDialog: false,
            pitfallContent: '',
            pendingLoading: false,
            pendingList: [],
            showReviewDialog: false,
            reviewTarget: null,
            reviewAction: 'approve',
            reviewRejectReason: '',
            reviewPublic: true,
            reviewSubmitting: false
        };
    },
    mounted() {
        this.fetchLegacy();
        if (this.canManage) this.fetchPending();
    },
    methods: {
        async fetchLegacy() {
            this.loading = true;
            try {
                const res = await axios.get('/api/legacy', { params: this.filters });
                this.legacyProjects = res.data || [];
            } catch (error) {
                ElementPlus.ElMessage.error('获取经验库失败');
            } finally {
                this.loading = false;
            }
        },
        async openDetail(row) {
            this.showDetail = true;
            this.detailLoading = true;
            this.currentLegacy = null;
            try {
                const res = await axios.get(`/api/legacy/${row.id}`);
                this.currentLegacy = res.data || null;
                if (this.currentLegacy) this.currentLegacy.is_borrowed = !!row.is_borrowed;
            } catch (e) {
                ElementPlus.ElMessage.error(e.response?.data?.error || e.response?.data?.message || '获取详情失败');
                this.showDetail = false;
            } finally {
                this.detailLoading = false;
            }
        },
        openBorrow(row) {
            this.borrowTarget = row;
            this.borrowReason = '';
            this.showBorrowDialog = true;
        },
        async submitBorrow() {
            if (!this.borrowTarget) return;
            try {
                const res = await axios.post(`/api/legacy/${this.borrowTarget.id}/borrow`, { reason: this.borrowReason });
                this.borrowTarget.is_borrowed = true;
                this.borrowTarget.borrowed_count = (res.data && res.data.borrowed_count) || this.borrowTarget.borrowed_count + 1;
                localStorage.setItem('legacy_inspiration_source_id', String(this.borrowTarget.id));
                localStorage.setItem('legacy_inspiration_source_title', this.borrowTarget.title || '');
                ElementPlus.ElMessage.success('借鉴成功，可在申报时关联该项目');
                this.showBorrowDialog = false;
            } catch (e) {
                ElementPlus.ElMessage.error(e.response?.data?.error || e.response?.data?.message || '借鉴失败');
            }
        },
        openPitfall() {
            this.pitfallContent = '';
            this.showPitfallDialog = true;
        },
        async submitPitfall() {
            if (!this.currentLegacy) return;
            if (!this.pitfallContent.trim()) {
                ElementPlus.ElMessage.warning('请输入避坑指南');
                return;
            }
            try {
                await axios.post(`/api/legacy/${this.currentLegacy.id}/pitfalls-suggestion`, { content: this.pitfallContent });
                ElementPlus.ElMessage.success('已提交，等待审核');
                this.showPitfallDialog = false;
            } catch (e) {
                ElementPlus.ElMessage.error(e.response?.data?.error || e.response?.data?.message || '提交失败');
            }
        },
        async fetchPending() {
            this.pendingLoading = true;
            try {
                const res = await axios.get('/api/legacy', { params: { status: 'pending' } });
                this.pendingList = res.data || [];
            } catch (e) {
                ElementPlus.ElMessage.error('获取待审核失败');
            } finally {
                this.pendingLoading = false;
            }
        },
        openReview(row, action) {
            this.reviewTarget = row;
            this.reviewAction = action;
            this.reviewRejectReason = '';
            this.reviewPublic = true;
            this.showReviewDialog = true;
        },
        async submitReview() {
            if (!this.reviewTarget) return;
            if (this.reviewAction === 'reject' && !this.reviewRejectReason.trim()) {
                ElementPlus.ElMessage.warning('请填写驳回原因');
                return;
            }
            this.reviewSubmitting = true;
            try {
                await axios.put(`/api/legacy/${this.reviewTarget.id}/review`, {
                    action: this.reviewAction,
                    is_public: this.reviewPublic ? 1 : 0,
                    reject_reason: this.reviewRejectReason
                });
                ElementPlus.ElMessage.success(this.reviewAction === 'approve' ? '已通过并入库' : '已驳回');
                this.showReviewDialog = false;
                await this.fetchPending();
            } catch (e) {
                ElementPlus.ElMessage.error(e.response?.data?.error || e.response?.data?.message || '操作失败');
            } finally {
                this.reviewSubmitting = false;
            }
        },
        downloadFile(file) {
            if (!file || !file.download_url) return;
            window.open(file.download_url, '_blank');
        },
        getCompetitionTypeLabel(v) {
            const s = String(v || '').trim();
            const map = {
                'challenge_cup': '“挑战杯”全国大学生课外学术科技作品竞赛',
                'internet_plus': '中国国际大学生创新大赛',
                'youth_challenge': '“挑战杯”中国大学生创业计划竞赛',
                'three_creativity_regular': '全国大学生电子商务“创新、创意及创业”挑战赛·常规赛',
                'three_creativity_practical': '全国大学生电子商务“创新、创意及创业”挑战赛·实战赛'
            };
            return map[s] || s || '竞赛';
        },
        getAwardLevelText(v) {
            const s = String(v || '').trim().toLowerCase();
            if (s === 'gold' || s === '金奖') return '金奖';
            if (s === 'silver' || s === '银奖') return '银奖';
            if (s === 'bronze' || s === '铜奖') return '铜奖';
            if (s === 'special' || s === '特等' || s === '特等奖') return '特等奖';
            if (s === 'first' || s === '一等' || s === '一等奖') return '一等奖';
            if (s === 'second' || s === '二等' || s === '二等奖') return '二等奖';
            if (s === 'third' || s === '三等' || s === '三等奖') return '三等奖';
            if (s === 'excellent' || s === '优秀奖' || s === '优秀') return '优秀';
            if (s === '良好') return '良好';
            if (s === '合格') return '合格';
            if (s === '不合格') return '不合格';
            if (s === 'none' || s === '无') return '无';
            return v || '';
        }
    },
    computed: {
        canManage() {
            return this.user && (this.user.role === 'system_admin' || this.user.role === 'project_admin' || this.user.role === 'school_approver');
        },
        competitionTypeOptions() {
            return [
                { label: '全部竞赛', value: 'all' },
                { label: '“挑战杯”全国大学生课外学术科技作品竞赛', value: 'challenge_cup' },
                { label: '中国国际大学生创新大赛', value: 'internet_plus' },
                { label: '“挑战杯”中国大学生创业计划竞赛', value: 'youth_challenge' },
                { label: '全国大学生电子商务“创新、创意及创业”挑战赛·常规赛', value: 'three_creativity_regular' },
                { label: '全国大学生电子商务“创新、创意及创业”挑战赛·实战赛', value: 'three_creativity_practical' }
            ];
        },
        awardLevelOptions() {
            return [
                { label: '全部级别', value: 'all' },
                { label: '特等奖', value: 'special' },
                { label: '一等奖', value: 'first' },
                { label: '二等奖', value: 'second' },
                { label: '三等奖', value: 'third' },
                { label: '金奖', value: 'gold' },
                { label: '银奖', value: 'silver' },
                { label: '铜奖', value: 'bronze' },
                { label: '优秀奖', value: 'excellent' }
            ];
        }
    }
};

const JiebangGuide = {
    template: `
    <div>
        <el-card shadow="never" style="margin-bottom: 16px;">
            <template #header>
                <div style="display:flex; align-items:center; justify-content:space-between;">
                    <span style="font-weight: 700;">2026揭榜挂帅选题指南</span>
                    <el-tag type="info">全量选题库</el-tag>
                </div>
            </template>
            <div style="color:#666; line-height: 20px;">
                本页面全文展示 11 大项目群全部选题，供申报“揭榜挂帅”专项参考。
            </div>
        </el-card>

        <el-card shadow="never">
            <el-skeleton v-if="loading" :rows="10" animated />
            <el-empty v-else-if="!tree.groups || tree.groups.length === 0" description="暂无选题库"></el-empty>
            <el-collapse v-else v-model="activeGroups">
                <el-collapse-item v-for="g in tree.groups" :key="g.group_no" :name="String(g.group_no)">
                    <template #title>
                        <span>{{ g.group_no }}. {{ g.group_name }}</span>
                    </template>
                    <div v-for="t in (g.topics || [])" :key="t.id" style="margin-bottom: 12px;">
                        <div style="font-weight: 600; line-height: 20px;">{{ g.group_no }}-{{ t.topic_no }} {{ t.topic_title }}</div>
                        <div style="color: #666; font-size: 13px; line-height: 18px;">{{ t.topic_desc }}</div>
                    </div>
                </el-collapse-item>
            </el-collapse>
        </el-card>
    </div>
    `,
    data() {
        return {
            year: 2026,
            loading: false,
            tree: { year: 2026, groups: [] },
            activeGroups: []
        };
    },
    async mounted() {
        await this.fetchTree();
    },
    methods: {
        async fetchTree() {
            this.loading = true;
            try {
                const res = await axios.get(`/api/jiebang/topics/tree?year=${this.year}`);
                const payload = res ? res.data : null;
                const data = payload && payload.year ? payload : (payload && payload.data ? payload.data : payload);
                this.tree = data && data.groups ? data : { year: this.year, groups: [] };
                const first = (this.tree.groups || [])[0];
                this.activeGroups = first ? [String(first.group_no)] : [];
            } catch (e) {
                console.error(e);
                this.tree = { year: this.year, groups: [] };
                ElementPlus.ElMessage.error(e.response?.data?.message || e.response?.data?.error || '获取选题库失败');
            } finally {
                this.loading = false;
            }
        }
    }
};

// 4. 个人中心组件
const Profile = {
    template: `
    <div class="profile-container">
        <el-card shadow="hover" class="mb-4">
            <template #header>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-weight: bold; font-size: 18px;"><el-icon><User /></el-icon> 基本信息</span>
                    <el-button type="primary" @click="updateProfile" :loading="updating">保存修改</el-button>
                </div>
            </template>
            <el-form :model="form" label-width="100px">
                <el-row :gutter="20">
                    <el-col :span="12">
                        <el-form-item label="用户名">
                            <el-input v-model="form.username" disabled></el-input>
                        </el-form-item>
                    </el-col>
                    <el-col :span="12">
                        <el-form-item label="姓名">
                            <el-input v-model="form.real_name"></el-input>
                        </el-form-item>
                    </el-col>
                </el-row>
                <el-row :gutter="20">
                    <el-col :span="12">
                        <el-form-item :label="getIdentityLabel(form.role)">
                            <el-input v-model="form.identity_number" disabled></el-input>
                        </el-form-item>
                    </el-col>
                    <el-col :span="12">
                        <el-form-item label="当前身份">
                            <el-tag>{{ getRoleText(form.role) }}</el-tag>
                        </el-form-item>
                    </el-col>
                </el-row>
                <el-row :gutter="20">
                    <el-col :span="12">
                        <el-form-item :label="getField1Label(form.role)">
                            <el-select v-model="form.college" filterable placeholder="请选择" style="width: 100%">
                                <el-option v-for="c in getField1Options(form.role)" :key="c" :label="c" :value="c"></el-option>
                            </el-select>
                        </el-form-item>
                    </el-col>
                    <el-col :span="12">
                        <el-form-item :label="getField2Label(form.role)">
                            <el-select v-model="form.department" filterable allow-create default-first-option placeholder="请选择" style="width: 100%">
                                <el-option v-for="d in getField2Options(form.role, form.college)" :key="d" :label="d" :value="d"></el-option>
                            </el-select>
                        </el-form-item>
                    </el-col>
                </el-row>
                <el-row :gutter="20">
                    <el-col :span="12">
                        <el-form-item label="邮箱">
                            <el-input v-model="form.email"></el-input>
                        </el-form-item>
                    </el-col>
                    <el-col :span="12">
                        <el-form-item label="联系电话">
                            <el-input v-model="form.phone"></el-input>
                        </el-form-item>
                    </el-col>
                </el-row>
                <el-form-item label="个人简介">
                    <el-input v-model="form.personal_info" type="textarea" :rows="3"></el-input>
                </el-form-item>
            </el-form>
        </el-card>

        <el-card shadow="hover">
            <template #header>
                <div style="font-weight: bold; font-size: 18px;"><el-icon><Lock /></el-icon> 修改密码</div>
            </template>
            <el-form :model="pwdForm" label-width="100px" style="max-width: 500px;">
                <el-form-item label="旧密码" required>
                    <el-input v-model="pwdForm.old_password" type="password" show-password></el-input>
                </el-form-item>
                <el-form-item label="新密码" required>
                    <el-input v-model="pwdForm.new_password" type="password" show-password></el-input>
                </el-form-item>
                <el-form-item label="确认新密码" required>
                    <el-input v-model="pwdForm.confirm_password" type="password" show-password></el-input>
                </el-form-item>
                <el-form-item>
                    <el-button type="warning" @click="changePassword" :loading="changingPwd">修改密码</el-button>
                </el-form-item>
            </el-form>
        </el-card>
    </div>
    `,
    props: ['user'],
    data() {
        return {
            form: {
                username: '',
                real_name: '',
                identity_number: '',
                role: '',
                college: '',
                department: '',
                email: '',
                phone: '',
                personal_info: ''
            },
            pwdForm: {
                old_password: '',
                new_password: '',
                confirm_password: ''
            },
            updating: false,
            changingPwd: false
        }
    },
    mounted() {
        this.fetchProfile();
    },
    methods: {
        async fetchProfile() {
            try {
                const res = await axios.get('/api/me');
                this.form = { ...this.form, ...res.data };
            } catch (error) {
                console.error(error);
            }
        },
        async updateProfile() {
            this.updating = true;
            try {
                await axios.put('/api/me', this.form);
                ElementPlus.ElMessage.success('个人信息更新成功');
            } catch (error) {
                ElementPlus.ElMessage.error(error.response?.data?.error || '更新失败');
            } finally {
                this.updating = false;
            }
        },
        async changePassword() {
            if (!this.pwdForm.old_password || !this.pwdForm.new_password) {
                ElementPlus.ElMessage.warning('请输入完整密码信息');
                return;
            }
            if (this.pwdForm.new_password !== this.pwdForm.confirm_password) {
                ElementPlus.ElMessage.warning('两次输入的新密码不一致');
                return;
            }
            this.changingPwd = true;
            try {
                await axios.put('/api/me/password', {
                    old_password: this.pwdForm.old_password,
                    new_password: this.pwdForm.new_password
                });
                ElementPlus.ElMessage.success('密码修改成功，请重新登录');
            } catch (error) {
                ElementPlus.ElMessage.error(error.response?.data?.error || '修改失败');
            } finally {
                this.changingPwd = false;
            }
        },
        getRoleText(role) {
            const map = {
                'student': '学生',
                'teacher': '指导老师',
                'college_approver': '学院审批人',
                'school_approver': '学校审批人',
                'judge': '评审专家',
                'project_admin': '项目管理员',
                'system_admin': '系统管理员'
            };
            return map[role] || role;
        },
        isOrgRole(role) {
            return ['system_admin', 'school_approver', 'project_admin'].includes(role);
        },
        getField1Label(role) {
            return this.isOrgRole(role) ? '所属部门' : '所属学院';
        },
        getField1Options(role) {
            return this.isOrgRole(role) ? ORG_DEPARTMENTS : CNMU_COLLEGES;
        },
        getIdentityLabel(role) {
            return role === 'student' ? '学号' : '工号';
        },
        getField2Label(role) {
            if (role === 'student') return '专业';
            if (['teacher', 'judge'].includes(role)) return '职称';
            return '职务';
        },
        getField2Options(role, field1Value) {
            if (role === 'student') return CNMU_COLLEGE_MAJOR[field1Value] || [];
            const arr = ROLE_FIELD2_OPTIONS[role];
            return Array.isArray(arr) ? arr : [];
        }
    }
};

// 5. Layout 组件
const Layout = {
    template: `
    <el-container class="app-wrapper">
        <el-aside width="240px" class="sidebar">
            <div class="logo">
                <el-icon size="24" color="var(--primary-color)"><Monitor /></el-icon>
                <span style="font-size: 16px; font-weight: 600; color: #2c3e50; margin-left: 10px;">大学生创新创业项目管理系统</span>
            </div>
            <el-menu :default-active="$route.path" router class="el-menu-vertical">
                <el-menu-item index="/">
                    <el-icon><DataLine /></el-icon>
                    <span>工作台</span>
                </el-menu-item>
                <el-menu-item index="/legacy">
                    <el-icon><Collection /></el-icon>
                    <span>往届项目经验库</span>
                </el-menu-item>
                <el-menu-item index="/jiebang-2026">
                    <el-icon><Document /></el-icon>
                    <span>2026揭榜挂帅选题指南</span>
                </el-menu-item>
                <el-menu-item index="/profile">
                    <el-icon><User /></el-icon>
                    <span>个人中心</span>
                </el-menu-item>
            </el-menu>
            
            <div class="sidebar-footer" style="padding: 20px; text-align: center; color: #909399; font-size: 12px; border-top: 1px solid #f0f0f0; margin-top: auto;">
                © 2025 大创管理系统
            </div>
        </el-aside>
        
        <el-container>
            <el-header class="header">
                <div class="header-left">
                    <el-breadcrumb separator="/">
                        <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
                        <el-breadcrumb-item>{{ breadcrumbName }}</el-breadcrumb-item>
                    </el-breadcrumb>
                </div>
                <div class="header-right">
                    <el-dropdown trigger="click">
                        <span class="user-info">
                            <el-avatar :size="32" icon="UserFilled" style="background: var(--primary-color);"></el-avatar>
                            <span class="username" style="margin-left: 8px; font-weight: 500;">{{ user?.real_name || user?.username }}</span>
                            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
                        </span>
                        <template #dropdown>
                            <el-dropdown-menu>
                                <el-dropdown-item v-if="user?.all_roles && user.all_roles.length > 1" header style="color: #999; font-size: 12px; padding: 5px 15px;">切换角色</el-dropdown-item>
                                <el-dropdown-item 
                                    v-for="r in user?.all_roles" 
                                    :key="r" 
                                    @click="switchRole(r)"
                                    :style="user?.active_role === r ? 'color: var(--primary-color); font-weight: bold;' : ''"
                                >
                                    {{ getRoleText(r) }}
                                </el-dropdown-item>
                                <el-divider v-if="user?.all_roles && user.all_roles.length > 1" style="margin: 5px 0;"></el-divider>
                                <el-dropdown-item @click="$router.push('/profile')">个人中心</el-dropdown-item>
                                <el-dropdown-item divided @click="logout" style="color: var(--danger-color);">退出登录</el-dropdown-item>
                            </el-dropdown-menu>
                        </template>
                    </el-dropdown>
                </div>
            </el-header>
            
            <el-main class="main-content">
                <router-view :user="user" @login-success="forwardLoginSuccess" @logout="forwardLogout"></router-view>
            </el-main>
        </el-container>
    </el-container>
    `,
    props: ['user'],
    computed: {
        breadcrumbName() {
            const map = { '/': '工作台', '/profile': '个人中心', '/legacy': '经验库', '/jiebang-2026': '2026揭榜挂帅选题指南' };
            return map[this.$route.path] || '首页';
        }
    },
    methods: {
        forwardLoginSuccess(u) {
            this.$emit('login-success', u);
        },
        forwardLogout() {
            this.$emit('logout');
        },
        async logout() {
            await axios.post('/api/logout');
            this.$emit('logout');
            this.$router.push('/login');
        },
        async switchRole(role) {
            if (this.user.active_role === role) return;
            try {
                await axios.post('/api/auth/switch_role', { role });
                ElementPlus.ElMessage.success(`已切换至 ${this.getRoleText(role)}`);
                // 重新加载页面以刷新所有权限
                window.location.reload();
            } catch (e) {
                ElementPlus.ElMessage.error(e.response?.data?.error || '切换失败');
            }
        },
        getRoleText(role) {
            const map = {
                'student': '学生',
                'teacher': '指导老师',
                'college_approver': '学院审批人',
                'school_approver': '学校审批人',
                'judge': '评审专家',
                'project_admin': '项目管理员',
                'system_admin': '系统管理员'
            };
            return map[role] || role;
        }
    }
};

// --- 初始化 ---
const routes = [
    { path: '/login', component: Login },
    { 
        path: '/', 
        component: Layout, 
        children: [
            { path: '', component: Dashboard },
            { path: 'legacy', component: LegacyLibrary },
            { path: 'jiebang-2026', component: JiebangGuide },
            { path: 'profile', component: Profile }
        ] 
    }
];
const router = createRouter({ history: createWebHashHistory(), routes });
const app = createApp({
    setup() {
        const user = ref(null);
        const sessionChecked = ref(false);
        try {
            const cached = localStorage.getItem('user_cache');
            if (cached) user.value = JSON.parse(cached);
        } catch (e) {}
        onMounted(async () => {
            try {
                const res = await axios.get('/api/me');
                user.value = res.data;
                sessionChecked.value = true;
                try { localStorage.setItem('user_cache', JSON.stringify(user.value)); } catch (e) {}
            } catch(e) {
                sessionChecked.value = true;
                user.value = null;
                try { localStorage.removeItem('user_cache'); } catch (e2) {}
                if(router.currentRoute.value.path !== '/login') router.push('/login');
            }
        });
        router.beforeEach(async (to, from, next) => {
            if (to.path !== '/login' && !sessionChecked.value) {
                try {
                    const res = await axios.get('/api/me');
                    user.value = res.data;
                    try { localStorage.setItem('user_cache', JSON.stringify(user.value)); } catch (e) {}
                    sessionChecked.value = true;
                    next();
                } catch (e) {
                    user.value = null;
                    try { localStorage.removeItem('user_cache'); } catch (e2) {}
                    sessionChecked.value = true;
                    next('/login');
                }
                return;
            }
            if (to.path !== '/login' && !user.value) {
                next('/login');
                return;
            }
            if (to.path === '/login' && user.value) {
                next('/');
                return;
            }
            next();
        });
        const handleLoginSuccess = async (u) => {
            user.value = u;
            try { localStorage.setItem('user_cache', JSON.stringify(u)); } catch (e) {}
            try {
                const fresh = await axios.get('/api/me');
                user.value = fresh.data;
                try { localStorage.setItem('user_cache', JSON.stringify(user.value)); } catch (e) {}
            } catch (e) {}
        };
        const handleLogout = () => {
            user.value = null;
            sessionChecked.value = true;
            try { localStorage.removeItem('user_cache'); } catch (e) {}
        };
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
