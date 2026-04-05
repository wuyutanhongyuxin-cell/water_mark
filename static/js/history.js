/**
 * 操作历史页面 Alpine.js 组件
 * 通过 API 获取并展示操作历史记录，支持分页和类型过滤
 */
function historyApp() {
    return {
        // 状态
        items: [],
        loading: false,
        filter: '',
        page: 1,
        pageSize: 20,
        total: 0,

        // 计算属性：总页数
        get totalPages() {
            return Math.ceil(this.total / this.pageSize) || 1;
        },

        // 加载历史记录
        async loadHistory() {
            this.loading = true;
            try {
                const params = new URLSearchParams({
                    page: this.page,
                    page_size: this.pageSize,
                });
                if (this.filter) {
                    params.set('operation', this.filter);
                }
                const resp = await fetch(`/api/tasks/history?${params}`);
                if (!resp.ok) throw new Error('加载失败');
                const data = await resp.json();
                this.items = data.items || [];
                this.total = data.total || 0;
            } catch (e) {
                console.error('加载历史记录失败:', e);
                this.items = [];
            } finally {
                this.loading = false;
            }
        },

        // 翻页
        prevPage() {
            if (this.page > 1) { this.page--; this.loadHistory(); }
        },
        nextPage() {
            if (this.page < this.totalPages) { this.page++; this.loadHistory(); }
        },

        // 格式化时间
        formatTime(ts) {
            if (!ts) return '-';
            try {
                const d = new Date(ts);
                const pad = n => String(n).padStart(2, '0');
                return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
            } catch {
                return ts;
            }
        },
    };
}
