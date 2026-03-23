export default {
    template: `
    <div class="profile-container">
        <el-card shadow="never" class="mb-4">
            <template #header>
                <div class="card-header">
                    <span>基本信息</span>
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
                        <el-form-item label="学号/工号">
                            <el-input v-model="form.identity_number" disabled></el-input>
                        </el-form-item>
                    </el-col>
                    <el-col :span="12">
                        <el-form-item label="角色">
                            <el-input :value="getRoleText(form.role)" disabled></el-input>
                        </el-form-item>
                    </el-col>
                </el-row>
                <el-row :gutter="20">
                    <el-col :span="12">
                        <el-form-item label="学院">
                            <el-input v-model="form.college"></el-input>
                        </el-form-item>
                    </el-col>
                    <el-col :span="12">
                        <el-form-item label="系/专业">
                            <el-input v-model="form.department"></el-input>
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

        <el-card shadow="never">
            <template #header>
                <span>修改密码</span>
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
                // Optional: Force logout
                // setTimeout(() => location.reload(), 1500);
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
        }
    }
}
