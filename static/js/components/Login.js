export default {
    template: `
    <div class="login-container">
        <el-card class="login-card">
            <template #header>
                <div class="card-header">
                    <h2>{{ isRegister ? '注册账号' : '欢迎登录' }}</h2>
                    <p class="subtitle">大学生创新创业项目管理系统</p>
                </div>
            </template>
            <el-form :model="form" label-position="top" size="large">
                <el-form-item label="用户名">
                    <el-input v-model="form.username" placeholder="请输入用户名" prefix-icon="User"></el-input>
                </el-form-item>
                <el-form-item label="密码">
                    <el-input v-model="form.password" type="password" placeholder="请输入密码" prefix-icon="Lock" show-password></el-input>
                </el-form-item>
                <el-form-item v-if="isRegister" label="角色">
                    <el-select v-model="form.role" placeholder="请选择角色" style="width: 100%">
                        <el-option label="学生" value="student"></el-option>
                        <el-option label="导师" value="teacher"></el-option>
                    </el-select>
                </el-form-item>
                <el-form-item>
                    <el-button type="primary" class="full-width-btn" @click="handleSubmit" :loading="loading">
                        {{ isRegister ? '立即注册' : '登录' }}
                    </el-button>
                </el-form-item>
                <div class="form-footer">
                    <el-button type="text" @click="toggleMode">
                        {{ isRegister ? '已有账号？去登录' : '没有账号？去注册' }}
                    </el-button>
                </div>
            </el-form>
            <div v-if="!isRegister" class="default-accounts" style="margin-top: 20px; padding: 10px; background: #f5f7fa; border-radius: 4px; font-size: 12px;">
                <p style="margin: 0 0 5px 0; font-weight: bold; color: #606266;">测试账号提示 (点击复制)：</p>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 5px; color: #909399;">
                    <div @click="fillAccount('admin', 'admin123')" style="cursor: pointer;">管理员: admin / admin123</div>
                    <div @click="fillAccount('proj_admin', 'admin123')" style="cursor: pointer;">项目管理: proj_admin / admin123</div>
                    <div @click="fillAccount('col_approver', 'admin123')" style="cursor: pointer;">学院审批: col_approver / admin123</div>
                    <div @click="fillAccount('sch_approver', 'admin123')" style="cursor: pointer;">学校审批: sch_approver / admin123</div>
                    <div @click="fillAccount('judge1', 'admin123')" style="cursor: pointer;">评委: judge1 / admin123</div>
                    <div @click="fillAccount('teacher1', 'teacher123')" style="cursor: pointer;">导师: teacher1 / teacher123</div>
                    <div @click="fillAccount('student1', 'student123')" style="cursor: pointer;">学生: student1 / student123</div>
                </div>
            </div>
        </el-card>
    </div>
    `,
    data() {
        return {
            isRegister: false,
            loading: false,
            form: {
                username: '',
                password: '',
                role: 'student'
            }
        }
    },
    methods: {
        fillAccount(u, p) {
            this.form.username = u;
            this.form.password = p;
            ElementPlus.ElMessage.success('已自动填充账号信息');
        },
        async handleSubmit() {
            if (!this.form.username || !this.form.password) {
                ElementPlus.ElMessage.warning('请输入用户名和密码');
                return;
            }
            
            this.loading = true;
            const endpoint = this.isRegister ? '/api/register' : '/api/login';
            
            try {
                const res = await axios.post(endpoint, this.form);
                if (this.isRegister) {
                    ElementPlus.ElMessage.success('注册成功，请登录');
                    this.isRegister = false;
                } else {
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
        toggleMode() {
            this.isRegister = !this.isRegister;
            this.form.username = '';
            this.form.password = '';
        }
    }
}
