/**
 * 提取页面 Alpine.js 组件
 * 管理单文件上传、水印提取请求、结果展示
 */
function extractApp() {
    return {
        // === 状态 ===
        file: null,              // 当前选中的文件（单文件）
        strength: 'medium',      // 提取强度
        processing: false,       // 是否正在处理
        result: null,            // 提取结果对象或 null
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
            const files = Array.from(fileList);
            if (files.length === 0) return;
            const check = validateFile(files[0]);
            if (check.valid) {
                this.file = files[0];
                this.result = null;
            } else {
                showToast(check.error, 'error');
            }
        },
        formatSize(bytes) {
            return formatFileSize(bytes);
        },

        // === 提交提取 ===
        async startExtract() {
            if (!this.file || this.processing) return;
            this.processing = true;
            this.result = null;

            try {
                const formData = new FormData();
                formData.append('file', this.file);
                formData.append('strength', this.strength);

                const resp = await fetch('/api/extract', {
                    method: 'POST', body: formData,
                });
                const data = await resp.json();

                if (!resp.ok) {
                    showToast(data.detail || '提取请求失败', 'error');
                    this.result = { success: false, message: data.detail || '请求失败' };
                } else {
                    this.result = data;
                }
            } catch (err) {
                showToast('提取请求异常: ' + err.message, 'error');
                this.result = { success: false, message: err.message };
            } finally {
                this.processing = false;
            }
        },
    };
}
