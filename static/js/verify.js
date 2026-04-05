/**
 * 验证页面 Alpine.js 组件
 * 管理多文件上传、单文件/批量验证请求、结果表格展示
 */
function verifyApp() {
    return {
        // === 状态 ===
        files: [],               // 已选文件列表
        expectedId: '',          // 预期员工 ID（可选）
        strength: 'medium',      // 提取强度
        processing: false,       // 是否正在处理
        results: null,           // 验证结果（null 或 VerifyBatchResponse 格式）
        dragover: false,         // 拖拽悬停状态

        // 强度选项
        strengthOptions: [
            { value: 'low', label: '低' },
            { value: 'medium', label: '中' },
            { value: 'high', label: '高' },
        ],

        // === 初始化 ===
        async init() {
            await loadConfig();
        },

        // === 文件操作 ===
        handleFiles(fileList) {
            const newFiles = Array.from(fileList);
            for (const file of newFiles) {
                const check = validateFile(file);
                if (check.valid) {
                    this.files.push(file);
                } else {
                    showToast(check.error, 'error');
                }
            }
        },
        removeFile(index) {
            this.files.splice(index, 1);
        },
        formatSize(bytes) {
            return formatFileSize(bytes);
        },

        // === 提交验证 ===
        async startVerify() {
            if (this.files.length === 0 || this.processing) return;
            this.processing = true;
            this.results = null;

            try {
                if (this.files.length === 1) {
                    await this._verifySingle(this.files[0]);
                } else {
                    await this._verifyBatch(this.files);
                }
            } catch (err) {
                showToast('验证请求异常: ' + err.message, 'error');
            } finally {
                this.processing = false;
            }
        },

        // 单文件验证
        async _verifySingle(file) {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('expected_id', this.expectedId.trim());
            formData.append('strength', this.strength);

            const resp = await fetch('/api/verify', { method: 'POST', body: formData });
            const data = await resp.json();

            if (!resp.ok) {
                showToast(data.detail || '验证请求失败', 'error');
                return;
            }
            // 统一为批量格式展示
            this.results = {
                total: 1,
                passed: (data.success && data.matched) ? 1 : 0,
                results: [{
                    filename: file.name,
                    success: data.success,
                    employee_id: data.employee_id || '',
                    matched: data.matched,
                    message: data.message || '',
                }],
            };
        },

        // 批量验证
        async _verifyBatch(files) {
            const formData = new FormData();
            files.forEach(f => formData.append('files', f));
            formData.append('expected_id', this.expectedId.trim());
            formData.append('strength', this.strength);

            const resp = await fetch('/api/verify/batch', { method: 'POST', body: formData });
            const data = await resp.json();

            if (!resp.ok) {
                showToast(data.detail || '批量验证请求失败', 'error');
                return;
            }
            this.results = data;
        },
    };
}
