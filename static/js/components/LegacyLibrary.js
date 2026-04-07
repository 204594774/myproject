
const LegacyLibrary = {
    template: `
    <div class="legacy-library">
        <el-card shadow="hover" class="mb-4">
            <template #header>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-weight: bold; font-size: 18px;">往届项目经验库</span>
                    <div style="display: flex; gap: 10px;">
                        <el-input 
                            v-model="filters.keyword" 
                            placeholder="搜索项目名称/方法论/避坑指南..." 
                            style="width: 300px;"
                            clearable
                            @clear="fetchLegacy"
                            @keyup.enter="fetchLegacy"
                        >
                            <template #prefix><el-icon><Search /></el-icon></template>
                        </el-input>
                        <el-select v-model="filters.category" placeholder="分类" @change="fetchLegacy" style="width: 150px;">
                            <el-option label="全部类别" value="all"></el-option>
                            <el-option label="创新类" value="innovation"></el-option>
                            <el-option label="创业类" value="entrepreneurship"></el-option>
                        </el-select>
                        <el-select v-model="filters.competition_type" placeholder="类型" @change="fetchLegacy" style="width: 170px;">
                            <el-option label="全部类型" value="all"></el-option>
                            <el-option label="大创创新训练" value="innovation"></el-option>
                            <el-option label="大创创业训练" value="entrepreneurship_training"></el-option>
                            <el-option label="大创创业实践" value="entrepreneurship_practice"></el-option>
                            <el-option label="“挑战杯”全国大学生课外学术科技作品竞赛" value="challenge_cup"></el-option>
                            <el-option label="中国国际大学生创新大赛" value="internet_plus"></el-option>
                            <el-option label="“挑战杯”中国大学生创业计划竞赛" value="youth_challenge"></el-option>
                            <el-option label="全国大学生电子商务“创新、创意及创业”挑战赛·常规赛" value="three_creativity_regular"></el-option>
                            <el-option label="全国大学生电子商务“创新、创意及创业”挑战赛·实战赛" value="three_creativity_practical"></el-option>
                        </el-select>
                        <el-select v-model="filters.award_level" placeholder="获奖" @change="fetchLegacy" style="width: 120px;">
                            <el-option label="全部获奖" value="all"></el-option>
                            <el-option label="金奖" value="gold"></el-option>
                            <el-option label="银奖" value="silver"></el-option>
                            <el-option label="铜奖" value="bronze"></el-option>
                            <el-option label="特等奖" value="special"></el-option>
                            <el-option label="一等奖" value="first"></el-option>
                            <el-option label="二等奖" value="second"></el-option>
                            <el-option label="三等奖" value="third"></el-option>
                            <el-option label="优秀奖" value="excellent"></el-option>
                        </el-select>
                        <el-button type="primary" @click="fetchLegacy">搜索</el-button>
                    </div>
                </div>
            </template>

            <el-table :data="legacyProjects" v-loading="loading" style="width: 100%">
                <el-table-column type="expand">
                    <template #default="scope">
                        <div style="padding: 20px; background: #fafafa; border-radius: 8px;">
                            <el-descriptions title="项目详细经验" :column="1" border>
                                <template v-if="scope.row.project_category === 'innovation'">
                                    <el-descriptions-item label="方法论总结">
                                        <div style="white-space: pre-wrap;">{{ scope.row.methodology_summary || '暂无总结' }}</div>
                                    </el-descriptions-item>
                                    <el-descriptions-item label="专家评语 (已脱敏)">
                                        <div style="white-space: pre-wrap; color: #67c23a;">{{ scope.row.expert_comments || '暂无评语' }}</div>
                                    </el-descriptions-item>
                                </template>
                                <template v-else>
                                    <el-descriptions-item label="行业领域">
                                        {{ scope.row.industry_field || '未填写' }}
                                    </el-descriptions-item>
                                    <el-descriptions-item label="团队经验">
                                        <div style="white-space: pre-wrap;">{{ scope.row.team_experience || '暂无经验' }}</div>
                                    </el-descriptions-item>
                                    <el-descriptions-item label="避坑指南">
                                        <div style="white-space: pre-wrap; color: #f56c6c;">{{ scope.row.pitfalls || '暂无指南' }}</div>
                                    </el-descriptions-item>
                                </template>
                            </el-descriptions>
                        </div>
                    </template>
                </el-table-column>
                
                <el-table-column prop="title" label="项目名称" min-width="250">
                    <template #default="scope">
                        <span style="font-weight: 500;">{{ scope.row.title }}</span>
                        <el-tag size="small" :type="scope.row.project_category === 'innovation' ? 'success' : 'warning'" style="margin-left: 8px;">
                            {{ scope.row.project_category === 'innovation' ? '创新类' : '创业类' }}
                        </el-tag>
                    </template>
                </el-table-column>
                
                <el-table-column label="获奖级别(省/国赛)" width="140">
                    <template #default="scope">
                        <el-tag size="small" effect="plain">{{ scope.row.award_level_display || scope.row.award_level_label || scope.row.award_level || '-' }}</el-tag>
                    </template>
                </el-table-column>

                <el-table-column label="被借鉴次数" width="120" align="center">
                    <template #default="scope">
                        <span style="font-weight: bold; color: #409eff;">{{ scope.row.borrowed_count }}</span>
                    </template>
                </el-table-column>

                <el-table-column label="操作" width="150" fixed="right">
                    <template #default="scope">
                        <el-button 
                            type="primary" 
                            size="small" 
                            :disabled="scope.row.is_borrowed"
                            @click="handleBorrow(scope.row)"
                        >
                            {{ scope.row.is_borrowed ? '已借鉴' : '借鉴此项目思路' }}
                        </el-button>
                    </template>
                </el-table-column>
            </el-table>
        </el-card>
    </div>
    `,
    props: ['user'],
    data() {
        return {
            loading: false,
            legacyProjects: [],
            filters: {
                keyword: '',
                category: 'all',
                competition_type: 'all',
                award_level: 'all'
            }
        };
    },
    mounted() {
        this.fetchLegacy();
    },
    methods: {
        async fetchLegacy() {
            this.loading = true;
            try {
                const res = await axios.get('/api/legacy', { params: this.filters });
                const payload = res.data;
                if (payload && typeof payload === 'object' && Object.prototype.hasOwnProperty.call(payload, 'code')) {
                    if (payload.code !== 200) throw new Error(payload.message || '获取经验库失败');
                    this.legacyProjects = Array.isArray(payload.data) ? payload.data : [];
                } else {
                    this.legacyProjects = Array.isArray(payload) ? payload : [];
                }
            } catch (error) {
                ElementPlus.ElMessage.error(error?.message || '获取经验库失败');
            } finally {
                this.loading = false;
            }
        },
        async handleBorrow(project) {
            try {
                const res = await axios.post(`/api/legacy/${project.id}/borrow`);
                const payload = res.data;
                if (payload && typeof payload === 'object' && Object.prototype.hasOwnProperty.call(payload, 'code') && payload.code !== 200) {
                    throw new Error(payload.message || '操作失败');
                }
                ElementPlus.ElMessage.success((payload && payload.message) ? payload.message : '借鉴成功！申报时可引用此项目思路');
                project.is_borrowed = true;
                const cnt = payload?.data?.borrowed_count;
                project.borrowed_count = (typeof cnt === 'number') ? cnt : ((Number(project.borrowed_count) || 0) + 1);
            } catch (error) {
                ElementPlus.ElMessage.error(error.message || '操作失败');
            }
        }
    }
};

export default LegacyLibrary;
