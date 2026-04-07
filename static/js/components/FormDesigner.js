const FIELD_LIBRARY = [
    { label: '项目名称', key: 'title', type: 'text', required: true, system: true, placeholder: '请输入项目名称' },
    { label: '项目类型', key: 'project_type', type: 'select', required: true, system: true, options: [], placeholder: '请选择项目类型' },
    { label: '研究周期', key: 'extra_info.duration', type: 'select', required: true, options: [{label:'1年',value:'1'}, {label:'2年',value:'2'}], placeholder: '请选择研究周期' },
    { label: '选题来源', key: 'extra_info.topic_source', type: 'select', required: true, options: [{label:'自主选题',value:'自主选题'},{label:'教师科研',value:'教师科研'},{label:'社会委托',value:'社会委托'},{label:'毕设选题',value:'毕设选题'},{label:'学院发布',value:'学院发布'},{label:'揭榜挂帅',value:'揭榜挂帅'}], placeholder: '请选择选题来源' },
    { label: '是否“揭榜挂帅”专项', key: 'extra_info.is_jiebang', type: 'radio', required: true, options: [{label:'是',value:'是'},{label:'否',value:'否'}], placeholder: '请选择' },
    { label: '重点支持项目', key: 'extra_info.is_key_support_candidate', type: 'radio', required: false, options: [{label:'是',value:'是'},{label:'否',value:'否'}], placeholder: '仅学院排序第1且已有成果可选' },
    { label: '所属学科', key: 'extra_info.subject', type: 'select', required: true, options: [], placeholder: '请选择所属学科' },
    { label: '项目简介', key: 'abstract', type: 'richtext', required: true, system: true, placeholder: '请输入项目简介' },
    { label: '创新点描述', key: 'extra_info.innovation_points', type: 'richtext', required: true, placeholder: '请输入创新点描述' },
    { label: '研究方案与技术路线', key: 'extra_info.research_plan', type: 'richtext', required: true, placeholder: '请输入研究方案与技术路线' },
    { label: '实施条件', key: 'extra_info.implementation_conditions', type: 'richtext', required: true, placeholder: '请输入实施条件' },
    { label: '预期成果', key: 'extra_info.expected_outcomes', type: 'checkbox', required: true, options: [{label:'论文',value:'paper'}, {label:'专利',value:'patent'}, {label:'软著',value:'software'}, {label:'实物',value:'product'}, {label:'调研报告',value:'report'}], placeholder: '请选择预期成果' },
    { label: '指导教师姓名', key: 'advisor_name', type: 'text', required: true, system: true, placeholder: '请输入指导教师姓名' },
    { label: '指导教师职称', key: 'extra_info.advisor_title', type: 'select', required: true, options: [{label:'教授',value:'教授'},{label:'副教授',value:'副教授'},{label:'讲师',value:'讲师'},{label:'助教',value:'助教'}], placeholder: '请选择职称' },
    { label: '指导教师所在单位', key: 'extra_info.advisor_org', type: 'text', required: true, placeholder: '请输入所在单位' },
    { label: '团队成员', key: 'members', type: 'table', required: true, system: true, placeholder: '请添加团队成员', columns: [{label:'学号',key:'student_id'},{label:'姓名',key:'name'},{label:'年级',key:'grade'},{label:'专业',key:'major'},{label:'角色',key:'role'}] },
    { label: '经费预算', key: 'extra_info.budget', type: 'table', required: true, placeholder: '请填写经费预算' },
    { label: '申报书附件', key: 'extra_info.attachments.application_doc', type: 'file', required: true, placeholder: '请上传申报书' },
    { label: '已有阶段性成果', key: 'extra_info.attachments.stage_achievement', type: 'file', required: false, placeholder: '可选；重点支持项目必填' },
    { label: '其他支撑材料', key: 'extra_info.attachments.other_support', type: 'file', required: false, placeholder: '可选' },
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

export default {
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
                // Allow removing system fields from the form view, but warn? No, user requested "删除不需要的字段".
                // But core system fields like ID might be needed. Let's allow deletion for now as requested.
                // Re-reading prompt: "✅ 删除不需要的字段".
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
                    </div>
                    <div class="field-actions">
                        <el-button size="small" circle icon="ArrowUp" @click="moveField(gIndex, fIndex, -1)" :disabled="fIndex === 0"></el-button>
                        <el-button size="small" circle icon="ArrowDown" @click="moveField(gIndex, fIndex, 1)" :disabled="fIndex === group.fields.length - 1"></el-button>
                        <el-button size="small" circle icon="Edit" @click="editField(gIndex, fIndex)"></el-button>
                        <el-button size="small" circle icon="Delete" type="danger" @click="removeField(gIndex, fIndex)"></el-button>
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
