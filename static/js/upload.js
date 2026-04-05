/**
 * 全局工具函数
 * 为各页面的 Alpine.js 组件提供通用工具方法
 */

/* ==========================================================================
 * 文件大小格式化
 * ========================================================================== */

/**
 * 格式化文件大小为人类可读字符串
 * @param {number} bytes - 字节数
 * @returns {string} 例如 "1.5 MB"
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    const size = (bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1);
    return size + ' ' + units[i];
}

/**
 * 获取文件扩展名（含点号，小写）
 * @param {string} filename
 * @returns {string} 例如 ".png"
 */
function getFileExtension(filename) {
    const dot = filename.lastIndexOf('.');
    if (dot === -1) return '';
    return filename.slice(dot).toLowerCase();
}

/**
 * 简单 HTML 转义（防 XSS）
 * @param {string} str
 * @returns {string}
 */
function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

/* ==========================================================================
 * Toast 通知
 * ========================================================================== */

/**
 * 显示 Toast 通知
 * @param {string} message - 通知内容
 * @param {'success'|'error'|'info'|'warning'} type - 通知类型
 * @param {number} duration - 显示时长（毫秒），默认 3500
 */
function showToast(message, type = 'info', duration = 3500) {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('toast-exit');
        toast.addEventListener('animationend', () => toast.remove());
    }, duration);
}

/* ==========================================================================
 * 文件校验工具
 * ========================================================================== */

/** @type {string[]} 支持的扩展名（由各页面 init() 从 /api/config 加载后更新） */
let _allowedExtensions = [];
/** @type {number} 最大文件字节数 */
let _maxFileSize = 500 * 1024 * 1024;

/**
 * 校验单个文件（扩展名 + 大小）
 * @param {File} file
 * @returns {{ valid: boolean, error: string }}
 */
function validateFile(file) {
    if (file.size === 0) {
        return { valid: false, error: `文件为空: ${file.name}` };
    }
    if (_allowedExtensions.length > 0) {
        const ext = getFileExtension(file.name);
        if (!_allowedExtensions.includes(ext)) {
            return { valid: false, error: `不支持的格式: ${ext || '(无扩展名)'}（${file.name}）` };
        }
    }
    if (file.size > _maxFileSize) {
        return { valid: false, error: `文件过大: ${formatFileSize(file.size)}（${file.name}）` };
    }
    return { valid: true, error: '' };
}

/**
 * 从 /api/config 加载配置并更新全局校验参数
 */
async function loadConfig() {
    try {
        const resp = await fetch('/api/config');
        const config = await resp.json();
        _allowedExtensions = config.supported_extensions || [];
        _maxFileSize = (config.max_file_size_mb || 500) * 1024 * 1024;
        return config;
    } catch {
        console.warn('[config] 无法获取服务端配置，使用默认值');
        return null;
    }
}

// 挂载到全局
window.formatFileSize = formatFileSize;
window.getFileExtension = getFileExtension;
window.escapeHtml = escapeHtml;
window.showToast = showToast;
window.validateFile = validateFile;
window.loadConfig = loadConfig;
