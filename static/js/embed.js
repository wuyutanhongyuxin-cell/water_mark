/**
 * 嵌入页面 Alpine.js 组件
 * 管理文件上传、参数配置、异步嵌入、SSE 进度追踪、结果展示
 */
function embedApp() {
    return {
        // === 状态 ===
        files: [],               // 已选文件列表
        employeeId: '',          // 员工 ID
        strength: 'medium',      // 水印强度
        autoVerify: true,        // 自动验证开关
        processing: false,       // 是否正在处理
        dragover: false,         // 拖拽悬停状态
        tasks: [],               // 任务进度列表 [{task_id, filename, status, progress, message}]
        results: [],             // 完成的结果列表 [{task_id, filename, success, message}]

        // === 计算属性 ===
        get totalSize() {
            return this.files.reduce((sum, f) => sum + f.size, 0);
        },
        get canSubmit() {
            return this.employeeId.trim().length > 0 && this.files.length > 0;
        },
        get successCount() {
            return this.results.filter(r => r.success).length;
        },

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

        // === 提交嵌入 ===
        async startEmbed() {
            if (!this.canSubmit || this.processing) return;
            this.processing = true;
            this.tasks = [];
            this.results = [];

            try {
                if (this.files.length === 1) {
                    await this._embedSingle(this.files[0]);
                } else {
                    await this._embedBatch(this.files);
                }
            } catch (err) {
                showToast('请求异常: ' + err.message, 'error');
                this.processing = false;
            }
        },

        // 单文件嵌入
        async _embedSingle(file) {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('employee_id', this.employeeId.trim());
            formData.append('strength', this.strength);
            formData.append('auto_verify', this.autoVerify);

            const resp = await fetch('/api/embed', { method: 'POST', body: formData });
            const data = await resp.json();
            if (!resp.ok) {
                showToast(data.detail || '嵌入请求失败', 'error');
                this.processing = false;
                return;
            }
            this._trackTask(data.task_id, file.name);
        },

        // 批量嵌入
        async _embedBatch(files) {
            const formData = new FormData();
            files.forEach(f => formData.append('files', f));
            formData.append('employee_id', this.employeeId.trim());
            formData.append('strength', this.strength);
            formData.append('auto_verify', this.autoVerify);

            const resp = await fetch('/api/embed/batch', { method: 'POST', body: formData });
            const data = await resp.json();
            if (!resp.ok) {
                showToast(data.detail || '批量嵌入请求失败', 'error');
                this.processing = false;
                return;
            }
            if (Array.isArray(data)) {
                data.forEach((task, i) => {
                    const name = files[i] ? files[i].name : `文件 ${i + 1}`;
                    if (task.task_id) {
                        this._trackTask(task.task_id, name);
                    } else {
                        // 文件校验失败
                        this.results.push({
                            task_id: '', filename: name,
                            success: false, message: task.message,
                        });
                    }
                });
            }
        },

        // 创建进度追踪并订阅 SSE
        _trackTask(taskId, filename) {
            const task = {
                task_id: taskId, filename,
                status: 'pending', progress: 0, message: '排队中...',
            };
            this.tasks.push(task);

            const sse = new SSEClient(`/api/tasks/${taskId}/events`, {
                onMessage: (evt) => {
                    task.status = evt.status || task.status;
                    task.progress = evt.progress || 0;
                    task.message = evt.message || '';
                },
                onComplete: (evt) => {
                    task.status = evt.status;
                    task.progress = evt.status === 'completed' ? 100 : 0;
                    task.message = evt.message || '';
                    this.results.push({
                        task_id: taskId, filename,
                        success: evt.status === 'completed',
                        message: evt.message || '',
                    });
                    this._checkAllDone();
                },
                onError: () => {
                    task.status = 'failed';
                    task.message = '连接断开';
                    this.results.push({
                        task_id: taskId, filename,
                        success: false, message: '连接断开',
                    });
                    this._checkAllDone();
                },
            });
            sse.connect();
        },

        // 检查是否所有任务已完成
        _checkAllDone() {
            const pending = this.tasks.filter(
                t => t.status !== 'completed' && t.status !== 'failed'
            );
            if (pending.length === 0) {
                this.processing = false;
            }
        },

        // 批量下载所有成功文件
        downloadAll() {
            const successes = this.results.filter(r => r.success && r.task_id);
            successes.forEach(r => {
                const a = document.createElement('a');
                a.href = `/api/embed/${r.task_id}/download`;
                a.download = '';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            });
        },
    };
}
