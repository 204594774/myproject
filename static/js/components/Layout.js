export default {
    template: `
    <el-container class="app-wrapper">
        <el-aside width="240px" class="sidebar">
            <div class="logo">
                <el-icon size="24" color="var(--primary-color)"><Monitor /></el-icon>
                <span style="font-size: 18px; font-weight: 600; color: #2c3e50; margin-left: 10px;">大创管理平台</span>
            </div>
            <el-menu :default-active="$route.path" router class="el-menu-vertical">
                <el-menu-item index="/">
                    <el-icon><DataLine /></el-icon>
                    <span>工作台</span>
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
                        <el-breadcrumb-item>{{ $route.path === '/profile' ? '个人中心' : '工作台' }}</el-breadcrumb-item>
                    </el-breadcrumb>
                </div>
                <div class="header-right">
                    <el-dropdown trigger="click">
                        <span class="user-info">
                            <el-avatar :size="32" icon="UserFilled" style="background: var(--primary-color);"></el-avatar>
                            <span class="username" style="margin-left: 8px; font-weight: 500;">{{ user?.real_name || user?.username }}</span>
                            <el-tag size="small" type="info" style="margin-left: 5px;">{{ roleText }}</el-tag>
                            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
                        </span>
                        <template #dropdown>
                            <el-dropdown-menu>
                                <el-dropdown-item @click="$router.push('/profile')">个人中心</el-dropdown-item>
                                <el-dropdown-item divided @click="logout" style="color: var(--danger-color);">退出登录</el-dropdown-item>
                            </el-dropdown-menu>
                        </template>
                    </el-dropdown>
                </div>
            </el-header>
            
            <el-main class="main-content">
                <router-view :user="user"></router-view>
            </el-main>
        </el-container>
    </el-container>
    `,
    props: ['user'],
    computed: {
        roleText() {
            if (!this.user) return '';
            const map = { 
                'student': '学生', 
                'teacher': '导师', 
                'system_admin': '管理员', 
                'project_admin': '项目管理员',
                'college_approver': '学院审批',
                'school_approver': '学校审批',
                'judge': '评委'
            };
            return map[this.user.role] || this.user.role;
        }
    },
    methods: {
        async logout() {
            try {
                await axios.post('/api/logout');
                this.$emit('logout');
                this.$router.push('/login');
                ElementPlus.ElMessage.success('已退出登录');
            } catch (error) {
                console.error(error);
            }
        }
    }
}
