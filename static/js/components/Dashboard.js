export default {
    template: `
    <div class="dashboard-container">
        <!-- 欢迎栏 -->
        <div class="welcome-banner" style="background: linear-gradient(120deg, #e0c3fc 0%, #8ec5fc 100%); padding: 20px; border-radius: 8px; margin-bottom: 20px; color: #5f2c82;">
            <div style="font-size: 20px; font-weight: bold;">
                <el-icon style="vertical-align: middle; margin-right: 5px;"><Sunrise /></el-icon>
                欢迎回来，{{ user?.real_name || user?.username }}
            </div>
            <div style="margin-top: 5px; opacity: 0.8;">
                当前角色：{{ getRoleName(user?.role) }} 
                <span v-if="user?.college"> | 所属：{{ user.college }}</span>
            </div>
        </div>

        <!-- 顶部统计卡片 -->
        <el-row :gutter="20" class="stat-row">
            <el-col :span="8">
                <el-card shadow="hover" class="stat-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-size: 14px; opacity: 0.8;">我的项目</div>
                            <div style="font-size: 36px; font-weight: bold; margin-top: 5px;">{{ myProjectsCount }}</div>
                        </div>
                        <el-icon size="48" style="opacity: 0.3;"><Folder /></el-icon>
                    </div>
                </el-card>
            </el-col>
            <el-col :span="8">
                <el-card shadow="hover" class="stat-card" style="background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 99%, #fecfef 100%); color: white;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-size: 14px; opacity: 0.8; color: #555;">待审核任务</div>
                            <div style="font-size: 36px; font-weight: bold; margin-top: 5px; color: #d9534f;">{{ pendingCount }}</div>
                        </div>
                        <el-icon size="48" style="opacity: 0.3; color: #555;"><Timer /></el-icon>
                    </div>
                </el-card>
            </el-col>
            <el-col :span="8">
                <el-card shadow="hover" class="stat-card" style="background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%); color: white;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-size: 14px; opacity: 0.8; color: #2c3e50;">已通过项目</div>
                            <div style="font-size: 36px; font-weight: bold; margin-top: 5px; color: #27ae60;">{{ approvedCount }}</div>
                        </div>
                        <el-icon size="48" style="opacity: 0.3; color: #2c3e50;"><CircleCheck /></el-icon>
                    </div>
                </el-card>
            </el-col>
        </el-row>

        <!-- 操作栏与筛选 -->
        <el-tabs v-model="activeTab" class="mt-4">
            <el-tab-pane label="项目管理" name="projects">
                <div class="action-bar" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 20px;">
                    <div style="display: flex; gap: 10px; align-items: center;">
                        <el-button v-if="user.role === 'student'" type="primary" @click="showCreateDialog = true" icon="Plus">
                            申请新项目
                        </el-button>
                    </div>
                    
                    <div class="filters" style="display: flex; gap: 10px;">
                        <el-select v-model="filters.year" placeholder="年份" clearable style="width: 100px">
                            <el-option label="2025" value="2025"></el-option>
                            <el-option label="2024" value="2024"></el-option>
                            <el-option label="2023" value="2023"></el-option>
                        </el-select>
                        <el-select v-model="filters.status" placeholder="状态" clearable style="width: 120px">
                            <el-option label="待审核" value="pending_audit"></el-option>
                            <el-option label="已通过" value="approved"></el-option>
                            <el-option label="已驳回" value="rejected"></el-option>
                        </el-select>
                        <el-select v-model="filters.type" placeholder="类型" clearable style="width: 120px">
                            <el-option label="创新训练" value="innovation"></el-option>
                            <el-option label="创业训练" value="entrepreneurship_training"></el-option>
                            <el-option label="创业实践" value="entrepreneurship_practice"></el-option>
                        </el-select>
                        <el-select v-if="['system_admin', 'project_admin', 'school_approver', 'college_approver'].includes(user.role)" v-model="filters.level" placeholder="级别" clearable style="width: 100px">
                            <el-option label="校级" value="school"></el-option>
                            <el-option label="省级" value="provincial"></el-option>
                            <el-option label="国家级" value="national"></el-option>
                        </el-select>
                        <el-input v-model="filters.keyword" placeholder="搜索项目/负责人" prefix-icon="Search" style="width: 150px" clearable></el-input>
                        
                        <el-button-group v-if="['system_admin', 'project_admin', 'school_approver', 'college_approver'].includes(user.role)">
                            <el-button type="success" icon="Download" @click="exportProjects">导出</el-button>
                            <el-button type="info" icon="DataLine" @click="showStatsDialog = true">统计</el-button>
                        </el-button-group>
                    </div>
                </div>
                
        <!-- 项目列表 -->
        <el-card class="table-card" shadow="never">
            <template #header>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-weight: bold; font-size: 16px;">项目列表</span>
                    <el-tag type="info" size="small">共 {{ filteredProjects.length }} 项</el-tag>
                </div>
            </template>
            <el-table :data="filteredProjects" style="width: 100%" v-loading="loading" :header-cell-style="{background:'#f5f7fa',color:'#606266'}">
                <el-table-column prop="title" label="项目名称" width="320">
                    <template #default="scope">
                        <el-tooltip :content="scope.row.title" placement="top" :show-after="300">
                            <span class="project-name" @click="viewDetails(scope.row.id)">{{ scope.row.title }}</span>
                        </el-tooltip>
                        <div style="font-size: 12px; color: #909399;">ID: {{ scope.row.id }} | {{ scope.row.year }}</div>
                    </template>
                </el-table-column>
                <el-table-column prop="leader_name" label="负责人" width="120">
                    <template #default="scope">
                        <div style="display: flex; align-items: center;">
                            <el-avatar :size="24" style="background:#f56c6c; margin-right: 5px;">{{ scope.row.leader_name?.[0] }}</el-avatar>
                            {{ scope.row.leader_name }}
                        </div>
                    </template>
                </el-table-column>
                <el-table-column prop="project_type" label="类型" width="120">
                    <template #default="scope">
                        <el-tag size="small" effect="plain">{{ scope.row.project_type === 'innovation' ? '创新训练' : (scope.row.project_type === 'entrepreneurship_training' ? '创业训练' : '创业实践') }}</el-tag>
                    </template>
                </el-table-column>
                <el-table-column prop="created_at" label="申请时间" width="180" sortable></el-table-column>
                <el-table-column prop="status" label="状态" width="140">
                    <template #default="scope">
                        <el-tag :type="getStatusType(scope.row.status)" effect="dark" style="border-radius: 12px;">{{ getStatusText(scope.row.status) }}</el-tag>
                    </template>
                </el-table-column>
                <el-table-column label="操作" min-width="200" fixed="right">
                    <template #default="scope">
                        <el-button-group>
                            <el-button size="small" icon="View" @click="viewDetails(scope.row.id)">详情</el-button>
                            <template v-if="canUserAudit(scope.row)">
                                <el-button size="small" type="success" icon="Check" @click.stop="openAuditDialog(scope.row, 'approved')">通过</el-button>
                                <el-button size="small" type="danger" icon="Close" @click.stop="openAuditDialog(scope.row, 'rejected')">驳回</el-button>
                            </template>
                            <template v-if="user.role === 'judge' && ['school_approved', 'rated'].includes(scope.row.status)">
                                 <el-button size="small" type="warning" icon="EditPen" @click.stop="openReviewDialog(scope.row)">评审</el-button>
                            </template>
                        </el-button-group>
                    </template>
                </el-table-column>
            </el-table>
        </el-card>
            </el-tab-pane>

            <!-- 评审任务 (评委) -->
            <el-tab-pane label="评审任务" name="reviews" v-if="user.role === 'judge'">
                 <el-card shadow="never">
                     <template #header>
                         <div style="display: flex; justify-content: space-between;">
                             <span>我的评审任务</span>
                             <el-button type="primary" size="small" @click="fetchReviewTasks">刷新</el-button>
                         </div>
                     </template>
                     <el-table :data="reviewTasks" style="width: 100%" v-loading="loadingReviews">
                         <el-table-column prop="title" label="项目名称" width="320">
                             <template #default="scope">
                                 <el-tooltip :content="scope.row.title" placement="top" :show-after="300">
                                     <span class="project-name" @click="openReviewDialog(scope.row)">{{ scope.row.title }}</span>
                                 </el-tooltip>
                             </template>
                         </el-table-column>
                         <el-table-column prop="project_type" label="类型"></el-table-column>
                         <el-table-column prop="status" label="任务状态">
                             <template #default="scope">
                                 <el-tag :type="scope.row.status === 'completed' ? 'success' : 'warning'">{{ scope.row.status === 'completed' ? '已完成' : '待评审' }}</el-tag>
                             </template>
                         </el-table-column>
                         <el-table-column label="操作">
                             <template #default="scope">
                                 <el-button size="small" type="primary" @click="openReviewDialog(scope.row)">去评审</el-button>
                             </template>
                         </el-table-column>
                     </el-table>
                 </el-card>
            </el-tab-pane>

            <!-- 系统管理 (管理员) -->
            <el-tab-pane label="系统日志" name="logs" v-if="user.role === 'system_admin'">
                 <el-card shadow="never">
                     <template #header>
                         <div style="display: flex; justify-content: space-between;">
                             <span>近期操作日志</span>
                             <el-button size="small" @click="fetchLogs">刷新</el-button>
                         </div>
                     </template>
                     <el-table :data="systemLogs" style="width: 100%" height="500">
                         <el-table-column prop="created_at" label="时间" width="180"></el-table-column>
                         <el-table-column prop="username" label="用户" width="120"></el-table-column>
                         <el-table-column prop="action" label="动作" width="150"></el-table-column>
                         <el-table-column prop="details" label="详情"></el-table-column>
                         <el-table-column prop="ip_address" label="IP" width="140"></el-table-column>
                     </el-table>
                 </el-card>
            </el-tab-pane>
        </el-tabs>
        
        <!-- 通知公告栏 (仅学生/导师可见) -->

        <!-- 创建项目弹窗 -->
        <el-dialog v-model="showCreateDialog" title="申请新项目" width="500px">
            <el-form :model="createForm" label-width="80px">
                <el-form-item label="项目名称">
                    <el-input v-model="createForm.title" placeholder="请输入项目名称"></el-input>
                </el-form-item>
                <el-form-item label="项目描述">
                    <el-input v-model="createForm.description" type="textarea" :rows="4" placeholder="简要描述项目内容..."></el-input>
                </el-form-item>
            </el-form>
            <template #footer>
                <span class="dialog-footer">
                    <el-button @click="showCreateDialog = false">取消</el-button>
                    <el-button type="primary" @click="submitProject" :loading="submitting">提交申请</el-button>
                </span>
            </template>
        </el-dialog>

        <!-- 详情/审核弹窗 -->
        <el-dialog v-model="showDetailDialog" :title="currentProject?.title" width="850px" top="5vh" destroy-on-close>
            <div v-if="currentProject" class="project-detail">
                
                <!-- 审核操作区 (置顶显示) -->
                <div v-if="isAuditing" class="audit-section mb-4 p-4" style="background-color: #fdf6ec; border: 1px solid #e6a23c; border-radius: 4px; margin-bottom: 20px;">
                    <div style="display: flex; align-items: center; margin-bottom: 10px;">
                        <el-icon size="20" :color="auditAction === 'approved' ? '#67c23a' : '#f56c6c'"><component :is="auditAction === 'approved' ? 'CircleCheck' : 'CircleClose'" /></el-icon>
                        <h3 style="margin: 0 0 0 10px; color: #303133;">{{ auditAction === 'approved' ? '通过审批' : '驳回申请' }}</h3>
                    </div>
                    <p style="color: #606266; font-size: 14px; margin-bottom: 10px;">您即将<strong>{{ auditAction === 'approved' ? '通过' : '驳回' }}</strong>该项目</p>
                    <el-input v-model="auditFeedback" placeholder="请输入审批意见（必填）" type="textarea" :rows="3"></el-input>
                    <div style="margin-top: 15px; text-align: right;">
                         <el-button @click="showDetailDialog = false">取消</el-button>
                         <el-button :type="auditAction === 'approved' ? 'success' : 'danger'" @click="confirmAudit" :loading="submitting">确认提交</el-button>
                    </div>
                </div>

                <!-- 评审操作区 (评委) -->
                <div v-if="isReviewing" class="review-section mb-4 p-4" style="background-color: #f0f9ff; border: 1px solid #409eff; border-radius: 4px; margin-bottom: 20px;">
                     <div style="display: flex; align-items: center; margin-bottom: 10px;">
                        <el-icon size="20" color="#409eff"><EditPen /></el-icon>
                        <h3 style="margin: 0 0 0 10px; color: #303133;">项目评审</h3>
                    </div>
                    
                    <el-form label-position="top">
                        <el-row :gutter="20">
                            <el-col :span="12">
                                <el-form-item label="创新性 (0-100)">
                                    <el-slider v-model="reviewForm.criteria_scores.innovation" show-input></el-slider>
                                </el-form-item>
                            </el-col>
                            <el-col :span="12">
                                <el-form-item label="可行性 (0-100)">
                                    <el-slider v-model="reviewForm.criteria_scores.feasibility" show-input></el-slider>
                                </el-form-item>
                            </el-col>
                            <el-col :span="12">
                                <el-form-item label="社会效益 (0-100)">
                                    <el-slider v-model="reviewForm.criteria_scores.benefit" show-input></el-slider>
                                </el-form-item>
                            </el-col>
                            <el-col :span="12">
                                <el-form-item label="综合评分 (自动计算)">
                                    <div style="font-size: 24px; font-weight: bold; color: #409eff;">{{ calculatedScore }}</div>
                                </el-form-item>
                            </el-col>
                        </el-row>
                        
                        <el-form-item label="评审意见">
                            <el-input v-model="reviewForm.comment" type="textarea" :rows="3" placeholder="请输入具体的评审意见..."></el-input>
                        </el-form-item>
                        
                        <div style="text-align: right;">
                            <el-button @click="showDetailDialog = false">取消</el-button>
                            <el-button type="primary" @click="submitReview" :loading="submitting">提交评审</el-button>
                        </div>
                    </el-form>
                </div>

                <!-- 动态过程步骤条 -->
                <el-steps v-if="projectProcess?.process_structure?.length" :active="getProcessActiveStep()" finish-status="success" align-center style="margin-bottom: 30px;">
                    <el-step v-for="node in projectProcess.process_structure" :key="node" :title="node">
                        <template #description>
                            <span style="font-size: 11px;">{{ projectProcess.node_current_status[node] || '待触发' }}</span>
                        </template>
                    </el-step>
                </el-steps>

                <!-- 传统状态步骤条 (作为回退) -->
                <el-steps v-else :active="getStepActive(currentProject.status)" finish-status="success" align-center style="margin-bottom: 30px;">
                    <el-step title="提交申请"></el-step>
                    <el-step :title="currentProject.project_type === 'challenge_cup' ? '指导教师初审' : '导师审核'"></el-step>
                    <el-step :title="currentProject.project_type === 'challenge_cup' ? '学院赛' : '学院审批'"></el-step>
                    <el-step :title="currentProject.project_type === 'challenge_cup' ? '校赛' : '学校审批'"></el-step>
                    <el-step :title="currentProject.project_type === 'challenge_cup' ? '省赛/国赛' : '立项完成'"></el-step>
                </el-steps>

                <el-descriptions :column="2" border title="基本信息" size="large">
                    <el-descriptions-item label="负责人">
                        <el-tag size="small">{{ currentProject.leader_name }}</el-tag>
                    </el-descriptions-item>
                    <el-descriptions-item label="当前状态">
                        <el-tag :type="getStatusType(currentProject.status)">{{ getStatusTextForRow(currentProject) }}</el-tag>
                    </el-descriptions-item>
                    <el-descriptions-item label="学院">{{ currentProject.college }}</el-descriptions-item>
                    <el-descriptions-item label="类型">{{ currentProject.project_type === 'innovation' ? '创新训练' : (currentProject.project_type === 'entrepreneurship_training' ? '创业训练' : (currentProject.project_type === 'challenge_cup' ? '挑战杯' : '创业实践')) }}</el-descriptions-item>
                </el-descriptions>
                <el-descriptions :column="2" border class="mt-2">
                    <el-descriptions-item label="项目ID">{{ currentProject.id }}</el-descriptions-item>
                    <el-descriptions-item label="年份">{{ currentProject.year }}</el-descriptions-item>
                    <el-descriptions-item label="级别">{{ currentProject.level }}</el-descriptions-item>
                    <el-descriptions-item label="指导老师">{{ currentProject.advisor_name }}</el-descriptions-item>
                    <el-descriptions-item label="系/专业">{{ currentProject.department }}</el-descriptions-item>
                    <el-descriptions-item label="申报人">{{ currentProject.leader_name }}</el-descriptions-item>
                </el-descriptions>

                <div v-if="currentProject.status === 'rejected' || currentProject.status?.includes('_rejected')" class="mt-3">
                    <el-descriptions :column="1" border>
                        <el-descriptions-item label="驳回层级">
                            {{
                                currentProject.extra_info?.rejection_level ||
                                (currentProject.school_feedback ? '学校' : (currentProject.college_feedback ? '学院' : (currentProject.extra_info?.advisor_feedback ? '导师' : '')))
                            }}
                        </el-descriptions-item>
                        <el-descriptions-item label="驳回理由">
                            {{
                                currentProject.extra_info?.rejection_reason ||
                                currentProject.school_feedback ||
                                currentProject.college_feedback ||
                                currentProject.extra_info?.advisor_feedback || '未提供'
                            }}
                        </el-descriptions-item>
                    </el-descriptions>
                </div>

                <div v-if="currentProject.project_type === 'innovation'" class="mt-4">
                    <el-divider content-position="left">立项详情</el-divider>
                    <el-descriptions :column="2" border>
                        <el-descriptions-item label="摘要">{{ currentProject.abstract }}</el-descriptions-item>
                        <el-descriptions-item label="指标">{{ currentProject.assessment_indicators }}</el-descriptions-item>
                        <el-descriptions-item label="创新点">{{ currentProject.innovation_point }}</el-descriptions-item>
                        <el-descriptions-item label="预期成果">{{ currentProject.expected_result }}</el-descriptions-item>
                        <el-descriptions-item label="预算">{{ currentProject.budget }}</el-descriptions-item>
                        <el-descriptions-item label="进度安排">{{ currentProject.schedule }}</el-descriptions-item>
                        <el-descriptions-item label="项目来源">{{ currentProject.project_source }}</el-descriptions-item>
                        <el-descriptions-item label="风险控制">{{ currentProject.risk_control }}</el-descriptions-item>
                    </el-descriptions>
                    <div class="mt-2">
                        <h4>背景与内容</h4>
                        <p style="white-space: pre-wrap;">{{ currentProject.background }}</p>
                        <p style="white-space: pre-wrap;">{{ currentProject.content }}</p>
                    </div>
                </div>

                <div v-else class="mt-4">
                    <el-divider content-position="left">创业项目信息</el-divider>
                    <el-descriptions :column="2" border>
                        <el-descriptions-item label="团队介绍">{{ currentProject.team_intro }}</el-descriptions-item>
                        <el-descriptions-item label="市场前景">{{ currentProject.market_prospect }}</el-descriptions-item>
                        <el-descriptions-item label="运营模式">{{ currentProject.operation_mode }}</el-descriptions-item>
                        <el-descriptions-item label="财务预算">{{ currentProject.financial_budget }}</el-descriptions-item>
                        <el-descriptions-item label="风险预算">{{ currentProject.risk_budget }}</el-descriptions-item>
                        <el-descriptions-item label="投资预算">{{ currentProject.investment_budget }}</el-descriptions-item>
                        <el-descriptions-item label="项目来源">{{ currentProject.project_source }}</el-descriptions-item>
                        <el-descriptions-item label="技术成熟度">{{ currentProject.tech_maturity }}</el-descriptions-item>
                        <el-descriptions-item label="企业导师">{{ currentProject.enterprise_mentor }}</el-descriptions-item>
                        <el-descriptions-item label="创新内容">{{ currentProject.innovation_content }}</el-descriptions-item>
                    </el-descriptions>
                </div>

                <div v-if="currentProject.members && currentProject.members.length" class="mt-4">
                    <h4>成员列表</h4>
                    <el-table :data="currentProject.members" border size="small">
                        <el-table-column prop="name" label="姓名"></el-table-column>
                        <el-table-column prop="student_id" label="学号"></el-table-column>
                        <el-table-column prop="college" label="学院"></el-table-column>
                        <el-table-column prop="major" label="专业"></el-table-column>
                        <el-table-column prop="contact" label="联系方式"></el-table-column>
                        <el-table-column prop="is_leader" label="负责人">
                            <template #default="scope">
                                <el-tag v-if="scope.row.is_leader" size="small" type="warning">是</el-tag>
                                <span v-else>否</span>
                            </template>
                        </el-table-column>
                    </el-table>
                </div>

                <!-- 过程管理详情 (管理岗可见) -->
                <div v-if="projectProcess?.process_structure?.length && ['school_approver', 'project_admin', 'system_admin', 'college_approver'].includes(user.role)" class="mt-4">
                    <el-divider content-position="left">过程节点管理</el-divider>
                    <el-table :data="projectProcess.process_structure" border size="small">
                        <el-table-column label="节点名称">
                            <template #default="scope">
                                <span style="font-weight: bold;">{{ scope.row }}</span>
                            </template>
                        </el-table-column>
                        <el-table-column label="当前状态">
                            <template #default="scope">
                                <el-tag size="small" :type="projectProcess.node_current_status[scope.row] ? 'success' : 'info'">
                                    {{ projectProcess.node_current_status[scope.row] || '待触发' }}
                                </el-tag>
                            </template>
                        </el-table-column>
                        <el-table-column label="审核意见" prop="comment">
                            <template #default="scope">
                                <span style="font-size: 12px; color: #666;">{{ projectProcess.node_comments[scope.row] || '-' }}</span>
                            </template>
                        </el-table-column>
                        <el-table-column label="操作" width="120" v-if="canEditProcessNode()">
                            <template #default="scope">
                                <el-button size="small" type="primary" link @click="openProcessEdit(scope.row)">录入/更新</el-button>
                            </template>
                        </el-table-column>
                    </el-table>
                </div>

                <div v-if="currentProject.files && currentProject.files.length && ['innovation', 'entrepreneurship_training', 'entrepreneurship_practice'].includes(currentProject.project_type)" class="mt-4">
                    <h4>项目过程材料</h4>
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
            </div>
            <template #footer>
                <span class="dialog-footer">
                    <el-button @click="showDetailDialog = false">关闭</el-button>
                </span>
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
                        <p>总申报数: {{ statsData.total_projects || 0 }}</p>
                        <p>总用户数: {{ statsData.total_users || 0 }}</p>
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

        <!-- 过程节点录入/更新对话框 -->
        <el-dialog v-model="showProcessEditDialog" :title="'节点管理: ' + processEditNode" width="500px">
            <el-form :model="processEditForm" label-width="100px">
                <el-form-item label="节点名称">
                    <el-tag>{{ processEditNode }}</el-tag>
                </el-form-item>
                <el-form-item label="更新状态" required>
                    <el-select v-model="processEditForm.current_status" placeholder="请选择状态" style="width: 100%">
                        <el-option v-for="opt in projectProcess?.node_options[processEditNode]" :key="opt" :label="opt" :value="opt"></el-option>
                    </el-select>
                </el-form-item>
                <el-form-item label="备注/意见" required>
                    <el-input type="textarea" v-model="processEditForm.comment" :rows="3" placeholder="请输入审批意见或备注"></el-input>
                </el-form-item>
                <el-form-item label="获奖等级" v-if="['省赛', '国赛'].includes(processEditNode)">
                    <el-input v-model="processEditForm.award_level" placeholder="例: 一等奖"></el-input>
                </el-form-item>
            </el-form>
            <template #footer>
                <el-button @click="showProcessEditDialog = false">取消</el-button>
                <el-button type="primary" @click="submitProcessUpdate">提交</el-button>
            </template>
        </el-dialog>
    </div>
    `,
    props: ['user'],
    data() {
        return {
            projects: [],
            loading: false,
            showCreateDialog: false,
            showDetailDialog: false,
            showStatsDialog: false,
            showNoticeDialog: false,
            submitting: false,
            activeTab: 'projects',
            createForm: {
                title: '',
                description: ''
            },
            currentProject: null,
            projectProcess: null,
            currentNotice: null,
            latestAnnouncement: null,
            isAuditing: false,
            isReviewing: false,
            auditAction: '',
            auditFeedback: '',
            reviewForm: {
                score: 0,
                comment: '',
                criteria_scores: {
                    innovation: 80,
                    feasibility: 80,
                    benefit: 80
                }
            },
            statsData: {},
            showProcessEditDialog: false,
            processEditNode: '',
            processEditForm: {
                current_status: '',
                comment: '',
                award_level: ''
            },
            reviewTasks: [],
            loadingReviews: false,
            systemLogs: [],
            filters: {
                year: '',
                status: '',
                type: '',
                level: '',
                keyword: ''
            }
        }
    },
    computed: {
        calculatedScore() {
            const { innovation, feasibility, benefit } = this.reviewForm.criteria_scores;
            return Math.round((innovation + feasibility + benefit) / 3);
        },
        filteredProjects() {
            return this.projects.filter(p => {
                // Year Filter
                if (this.filters.year && p.year !== this.filters.year) return false;
                
                // Status Filter
                if (this.filters.status) {
                    if (this.filters.status === 'pending_audit') {
                        // Complex logic: what is pending for THIS user?
                        if (!this.canUserAudit(p)) return false;
                    } else if (this.filters.status === 'approved') {
                        if (!this.isApprovedStatus(p.status)) return false;
                    } else if (this.filters.status === 'rejected') {
                        if (!this.isRejectedStatus(p.status)) return false;
                    }
                }
                
                // Type Filter
                if (this.filters.type && p.project_type !== this.filters.type) return false;
                
                // Level Filter
                if (this.filters.level) {
                    const lv = this.normalizeLevel(p.level || p.project_level || p.current_level || '');
                    if (lv !== this.filters.level) return false;
                }
                
                // Keyword Filter
                if (this.filters.keyword) {
                    const k = this.filters.keyword.toLowerCase();
                    const match = (p.title && p.title.toLowerCase().includes(k)) || 
                                  (p.leader_name && p.leader_name.toLowerCase().includes(k));
                    if (!match) return false;
                }
                
                return true;
            });
        },
        canAudit() {
            return ['teacher', 'admin', 'college_approver', 'school_approver'].includes(this.user.role);
        },
        myProjectsCount() {
            return this.projects.length;
        },
        pendingCount() {
            return this.projects.filter(p => this.canUserAudit(p)).length;
        },
        approvedCount() {
            return this.projects.filter(p => this.isApprovedStatus(p.status)).length;
        }
    },
    mounted() {
        this.fetchProjects();
        if (['student', 'teacher'].includes(this.user.role)) {
            this.fetchAnnouncements();
        }
    },
    methods: {
        async fetchAnnouncements() {
            try {
                const res = await axios.get('/api/announcements');
                if (res.data && res.data.length > 0) {
                    this.latestAnnouncement = res.data[0];
                }
            } catch (e) { console.error(e); }
        },
        viewAnnouncement(notice) {
            this.currentNotice = notice;
            this.showNoticeDialog = true;
        },
        exportProjects() {
            window.location.href = '/api/reports/export';
        },
        async initCharts() {
            try {
                const res = await axios.get('/api/stats');
                this.statsData = (res.data && res.data.data) ? res.data.data : (res.data || {});
                
                this.$nextTick(() => {
                    // Status Chart
                    const statusChart = echarts.init(document.getElementById('statusChart'));
                    statusChart.setOption({
                        title: { text: '项目状态分布' },
                        tooltip: { trigger: 'item' },
                        series: [{
                            type: 'pie',
                            radius: '50%',
                            data: (this.statsData.project_stats || []).map(s => ({ name: this.getStatusText(s.status), value: s.count }))
                        }]
                    });
                    
                    // College Chart
                    const collegeChart = echarts.init(document.getElementById('collegeChart'));
                    collegeChart.setOption({
                        title: { text: '学院申报分布' },
                        tooltip: { trigger: 'axis' },
                        xAxis: { type: 'category', data: (this.statsData.college_stats || []).map(s => s.college) },
                        yAxis: { type: 'value' },
                        series: [{
                            type: 'bar',
                            data: (this.statsData.college_stats || []).map(s => s.count)
                        }]
                    });
                    
                    // Type Chart
                    const typeChart = echarts.init(document.getElementById('typeChart'));
                    typeChart.setOption({
                        title: { text: '项目类型分布' },
                        tooltip: { trigger: 'item' },
                        series: [{
                            type: 'pie',
                            radius: ['40%', '70%'],
                            data: (this.statsData.type_stats || []).map(s => ({ 
                                name: s.project_type === 'innovation' ? '创新训练' : (s.project_type === 'entrepreneurship_training' ? '创业训练' : '创业实践'), 
                                value: s.count 
                            }))
                        }]
                    });
                });
            } catch (e) {
                console.error(e);
                ElementPlus.ElMessage.error('获取统计数据失败');
            }
        },
        canUserAudit(project) {
            if (!this.user) return false;
            const role = this.user.role;
            const status = project.status;
            
            if (role === 'teacher') {
                return ['pending_teacher', 'pending', 'pending_advisor_review', 'midterm_submitted', 'conclusion_submitted'].includes(status);
            }
            if (role === 'college_approver') {
                return ['pending_college', 'advisor_approved', 'midterm_advisor_approved', 'conclusion_advisor_approved'].includes(status);
            }
            if (role === 'school_approver') {
                return ['college_recommended', 'pending_college', 'college_approved', 'midterm_college_approved', 'conclusion_college_approved'].includes(status);
            }
            return false;
        },
        async fetchProjects() {
            this.loading = true;
            try {
                const res = await axios.get(`/api/projects?t=${new Date().getTime()}`);
                // 清除硬编码的 ID 过滤 (6, 7, 8, 9)
                this.projects = Array.isArray(res.data) 
                    ? res.data.filter(p => p && p.id && !isNaN(Number(p.id)) && Number(p.id) > 0) 
                    : [];
            } catch (error) {
                console.error(error);
                if (error.response?.status === 401) {
                    this.$router.push('/login');
                }
            } finally {
                this.loading = false;
            }
        },
        async submitProject() {
            if (!this.createForm.title || !this.createForm.description) {
                ElementPlus.ElMessage.warning('请填写完整信息');
                return;
            }
            this.submitting = true;
            try {
                await axios.post('/api/projects', this.createForm);
                ElementPlus.ElMessage.success('申请提交成功');
                this.showCreateDialog = false;
                this.createForm = { title: '', description: '' };
                this.fetchProjects();
            } catch (error) {
                ElementPlus.ElMessage.error(error && error.message ? error.message : '提交失败');
            } finally {
                this.submitting = false;
            }
        },
        async viewDetails(id) {
            try {
                const [projRes, procRes] = await Promise.all([
                    axios.get(`/api/projects/${id}?t=${new Date().getTime()}`),
                    axios.get(`/api/projects/${id}/process?t=${new Date().getTime()}`)
                ]);
                this.currentProject = projRes.data;
                this.projectProcess = procRes.data;
                this.isAuditing = false;
                this.showDetailDialog = true;
            } catch(e) {
                console.error(e);
                ElementPlus.ElMessage.error('获取详情失败');
            }
        },
        openAuditDialog(project, action) {
            this.currentProject = project;
            this.auditAction = action;
            this.isAuditing = true;
            this.auditFeedback = '';
            this.showDetailDialog = true;
        },
        async confirmAudit() {
            this.submitting = true;
            try {
                const action = this.auditAction === 'approved' ? 'approve' : 'reject';
                const feedback = String(this.auditFeedback || '').trim();
                const st = String(this.currentProject?.status || '').trim();
                if (st === 'pending_advisor_review') {
                    if (!feedback) {
                        ElementPlus.ElMessage.warning('审批意见为必填项');
                        this.submitting = false;
                        return;
                    }
                    await axios.post(`/api/projects/${this.currentProject.id}/advisor_review`, {
                        status: action === 'approve' ? 'pass' : 'reject',
                        opinion: feedback
                    });
                    ElementPlus.ElMessage.success('初审操作成功');
                } else {
                    if (action === 'reject' && !feedback) {
                        ElementPlus.ElMessage.warning('驳回时审批意见为必填项');
                        this.submitting = false;
                        return;
                    }
                    await axios.put(`/api/projects/${this.currentProject.id}/audit`, {
                        action,
                        feedback
                    });
                    ElementPlus.ElMessage.success('审批成功');
                }
                this.showDetailDialog = false;
                this.fetchProjects();
            } catch (error) {
                const msg = (error && error.response && error.response.data && (error.response.data.message || error.response.data.error))
                    || (error && error.message)
                    || '操作失败';
                ElementPlus.ElMessage.error(msg);
            } finally {
                this.submitting = false;
            }
        },
        getProcessActiveStep() {
            if (!this.projectProcess || !this.projectProcess.process_structure) return 0;
            const structure = this.projectProcess.process_structure;
            const statuses = this.projectProcess.node_current_status;
            
            let lastActive = 0;
            for (let i = 0; i < structure.length; i++) {
                const node = structure[i];
                const status = statuses[node];
                
                if (status && status !== '待触发' && !status.includes('待评审') && !status.includes('待初审')) {
                    lastActive = i + 1;
                } else if (status && (status.includes('待评审') || status.includes('待初审'))) {
                    return i;
                }
            }
            return lastActive;
        },
        canEditProcessNode() {
            if (!this.user) return false;
            const role = this.user.role;
            // 学校管理员和系统管理员可以编辑所有节点（省赛/国赛录入）
            if (['school_approver', 'system_admin', 'project_admin'].includes(role)) return true;
            // 学院管理员可以编辑特定的初级节点
            if (role === 'college_approver') return true; 
            return false;
        },
        openProcessEdit(nodeName) {
            this.processEditNode = nodeName;
            this.processEditForm = {
                current_status: this.projectProcess.node_current_status[nodeName] || '',
                comment: this.projectProcess.node_comments[nodeName] || '',
                award_level: ''
            };
            this.showProcessEditDialog = true;
        },
        async submitProcessUpdate() {
            if (!this.processEditForm.current_status) {
                ElementPlus.ElMessage.warning('请选择状态');
                return;
            }
            if (!this.processEditForm.comment) {
                ElementPlus.ElMessage.warning('审批意见为必填项');
                return;
            }
            
            try {
                await axios.put(`/api/projects/${this.currentProject.id}/process`, {
                    node_name: this.processEditNode,
                    ...this.processEditForm
                });
                ElementPlus.ElMessage.success('更新成功');
                this.showProcessEditDialog = false;
                // 刷新详情
                await this.viewDetails(this.currentProject.id);
            } catch(e) {
                console.error(e);
                ElementPlus.ElMessage.error(e.response?.data?.message || e.response?.data?.error || e?.message || '更新失败');
            }
        },
        getStatusType(status) {
            const map = {
                'pending': 'warning',
                'pending_teacher': 'warning',
                'pending_college': 'warning',
                'reviewing': 'warning',
                'college_recommended': 'primary',
                'approved': 'success',
                'pending_advisor_review': 'warning',
                'college_review': 'warning',
                'school_review': 'warning',
                'to_modify': 'danger',
                'advisor_approved': 'primary',
                'college_approved': 'primary',
                'school_approved': 'info',
                'rated': 'success',
                'rejected': 'danger',
                'midterm_submitted': 'warning',
                'midterm_advisor_approved': 'primary',
                'midterm_college_approved': 'primary',
                'midterm_approved': 'success',
                'midterm_rejected': 'danger',
                'conclusion_submitted': 'warning',
                'conclusion_advisor_approved': 'primary',
                'conclusion_college_approved': 'primary',
                'finished': 'success',
                'finished_national_award': 'success',
                'conclusion_rejected': 'danger'
            };
            return map[status] || 'info';
        },
        getStatusText(status) {
            const map = {
                'pending': '待导师审核',
                'pending_teacher': '待导师审核',
                'pending_college': '待学院审核',
                'reviewing': '学院评委盲评中',
                'college_recommended': '学院评审完成',
                'approved': '校级通过（公开）',
                'pending_advisor_review': '待指导教师初审',
                'college_review': '待评审（学院赛）',
                'school_review': '待评审（校赛）',
                'to_modify': '待修改',
                'advisor_approved': '待学院审批',
                'college_approved': '待学校审批',
                'school_approved': '待评审',
                'rated': '已评审',
                'rejected': '已驳回',
                'midterm_submitted': '中期-待导师审核',
                'midterm_advisor_approved': '中期-待学院审核',
                'midterm_college_approved': '中期-待学校审核',
                'midterm_approved': '中期检查通过',
                'midterm_rejected': '中期-已驳回',
                'conclusion_submitted': '结项-待导师审核',
                'conclusion_advisor_approved': '结项-待学院审核',
                'conclusion_college_approved': '结项-待学校审核',
                'finished': '已结项',
                'finished_national_award': '已结项·国赛获奖',
                'conclusion_rejected': '结项-已驳回'
            };
            return map[status] || status;
        },
        normalizeLevel(v) {
            const raw = String(v || '').trim();
            const s = raw.toLowerCase();
            if (!s) return '';
            if (['school', '校级', '院级'].includes(s) || raw === '校级') return 'school';
            if (['provincial', 'province', '省级'].includes(s) || raw === '省级' || raw === '省赛获奖') return 'provincial';
            if (['national', 'country', '国家级'].includes(s) || raw === '国家级' || raw === '国赛获奖') return 'national';
            return s;
        },
        isApprovedStatus(status) {
            const s = String(status || '').trim();
            return ['approved', 'school_approved', 'rated', 'midterm_approved', 'finished', 'finished_national_award'].includes(s);
        },
        isRejectedStatus(status) {
            const s = String(status || '').trim();
            if (!s) return false;
            return s === 'rejected' || s.endsWith('_rejected') || s.endsWith('_failed') || s.includes('failed');
        },
        getStepActive(status) {
            const s = status;
            if (['pending_teacher', 'pending', 'pending_advisor_review'].includes(s)) return 1;
            if (['pending_college', 'advisor_approved', 'college_review'].includes(s)) return 2;
            if (['reviewing', 'college_approved', 'school_review', 'college_recommended'].includes(s)) return 3;
            if (['approved', 'school_approved'].includes(s)) return 4;
            if (['rated', 'finished'].includes(s) || (s && (s.startsWith('midterm') || s.startsWith('conclusion')))) return 5;
            return 0;
        },
        getStatusTextForRow(row) {
            const base = this.getStatusText(row.status);
            const isRejected = row.status === 'rejected' || (typeof row.status === 'string' && row.status.endsWith('_rejected'));
            if (!isRejected) return base;
            const level = row.extra_info?.rejection_level
                || (row.school_feedback ? '学校' : (row.college_feedback ? '学院' : (row.extra_info?.advisor_feedback ? '学院（导师）' : '')));
            return level ? `${level}已驳回` : base;
        },
        async fetchReviewTasks() {
            if (this.user.role !== 'judge') return;
            this.loadingReviews = true;
            try {
                const res = await axios.get('/api/reviews/tasks');
                this.reviewTasks = res.data.tasks;
            } catch (error) {
                console.error(error);
            } finally {
                this.loadingReviews = false;
            }
        },
        async fetchLogs() {
             if (this.user.role !== 'system_admin') return;
             try {
                 const res = await axios.get('/api/admin/logs?limit=50');
                 this.systemLogs = res.data;
             } catch(e) { console.error(e); }
        },
        openReviewDialog(project) {
            this.currentProject = project;
            this.isReviewing = true;
            this.isAuditing = false;
            this.reviewForm = {
                score: 0,
                comment: '',
                criteria_scores: { innovation: 80, feasibility: 80, benefit: 80 }
            };
            this.showDetailDialog = true;
        },
        async submitReview() {
            this.submitting = true;
            try {
                this.reviewForm.score = this.calculatedScore;
                await axios.post(`/api/projects/${this.currentProject.id}/review`, this.reviewForm);
                ElementPlus.ElMessage.success('评审提交成功');
                this.showDetailDialog = false;
                this.fetchReviewTasks(); // Refresh tasks
                this.fetchProjects(); // Refresh project list
            } catch (error) {
                ElementPlus.ElMessage.error(error.response?.data?.error || '提交失败');
            } finally {
                this.submitting = false;
            }
        }
    },
    watch: {
        activeTab(val) {
            if (val === 'reviews') this.fetchReviewTasks();
            if (val === 'logs') this.fetchLogs();
        }
    }
}
