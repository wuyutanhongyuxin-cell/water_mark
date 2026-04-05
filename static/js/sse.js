/**
 * SSE (Server-Sent Events) 连接管理工具
 * 用于接收服务端实时进度推送，例如水印嵌入任务的进度更新
 *
 * 使用方式:
 *   const sse = new SSEClient('/api/tasks/xxx/events', {
 *       onMessage:  (data) => { ... },   // 每次收到消息
 *       onComplete: (data) => { ... },   // 任务完成或失败
 *       onError:    (err)  => { ... },   // 连接异常
 *   });
 *   sse.connect();
 *   // 不再需要时: sse.close();
 */

class SSEClient {
    /**
     * @param {string} url       - SSE 端点地址
     * @param {Object} options   - 回调函数配置
     * @param {Function} options.onMessage  - 收到消息时的回调，参数为解析后的 JSON 对象
     * @param {Function} options.onError    - 连接出错时的回调
     * @param {Function} options.onComplete - 任务终态（completed / failed）时的回调
     * @param {number}   options.maxRetries - 最大自动重连次数，默认 3
     */
    constructor(url, options = {}) {
        this.url = url;
        this.onMessage = options.onMessage || (() => {});
        this.onError = options.onError || (() => {});
        this.onComplete = options.onComplete || (() => {});
        this.maxRetries = options.maxRetries ?? 3;

        /** @type {EventSource|null} */
        this.eventSource = null;
        this._retryCount = 0;
        this._closed = false;  // 手动关闭标记，防止自动重连
    }

    /**
     * 建立 SSE 连接并开始监听事件
     */
    connect() {
        // 防止重复连接
        if (this.eventSource) {
            this.close();
        }
        this._closed = false;

        this.eventSource = new EventSource(this.url);

        // 收到消息
        this.eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.onMessage(data);

                // 检测终态：任务完成或失败时关闭连接
                if (data.status === 'completed' || data.status === 'failed') {
                    this.close();
                    this.onComplete(data);
                }
            } catch (parseErr) {
                console.warn('[SSE] 消息解析失败:', parseErr, event.data);
            }
        };

        // 连接异常处理
        this.eventSource.onerror = (err) => {
            // EventSource 自身会尝试重连，但我们限制最大次数
            this._retryCount++;

            if (this._retryCount > this.maxRetries || this._closed) {
                // 超过重试上限或已手动关闭，停止连接
                this.close();
                this.onError(err);
            }
            // 未超过上限时，浏览器会自动重连，无需额外处理
        };
    }

    /**
     * 关闭 SSE 连接，释放资源
     */
    close() {
        this._closed = true;
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
    }

    /**
     * 当前连接是否处于活跃状态
     * @returns {boolean}
     */
    isConnected() {
        return this.eventSource !== null &&
               this.eventSource.readyState !== EventSource.CLOSED;
    }
}

// 挂载到全局，供各页面脚本使用
window.SSEClient = SSEClient;
