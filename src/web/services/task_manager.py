"""
异步任务管理器。

线程安全地管理水印处理任务的状态，支持：
- 任务创建/更新/查询
- SSE 事件推送（实时进度通知）
- 操作历史记录（内存分页查询）
"""

import asyncio
import datetime
import json
import threading
import uuid
from dataclasses import dataclass, field
from typing import AsyncGenerator, Optional

from loguru import logger

from src.web.schemas import HistoryItem, TaskResponse, TaskStatus
from src.web.services.cleanup import cleanup_old_files, run_cleanup_daemon


@dataclass
class TaskInfo:
    """内部任务信息（dataclass，不暴露给 API）。"""
    task_id: str
    filename: str
    operation: str            # embed / extract / verify
    status: TaskStatus = TaskStatus.PENDING
    progress: int = 0
    message: str = ""
    employee_id: str = ""
    output_path: Optional[str] = None   # 嵌入完成后的输出路径
    created_at: str = ""
    extra: dict = field(default_factory=dict)


class TaskManager:
    """管理异步任务状态和 SSE 事件分发。"""

    def __init__(self):
        self._tasks: dict[str, TaskInfo] = {}
        self._lock = threading.Lock()
        # SSE 事件队列：task_id -> asyncio.Queue 列表（支持多个订阅者）
        self._events: dict[str, list[asyncio.Queue]] = {}
        self._history: list[HistoryItem] = []
        # 启动清理守护线程
        self._cleanup_thread = threading.Thread(
            target=run_cleanup_daemon, daemon=True,
        )
        self._cleanup_thread.start()

    def create_task(self, filename: str, operation: str) -> str:
        """创建新任务，返回 task_id（uuid4 前12位）。"""
        task_id = uuid.uuid4().hex[:12]
        now = datetime.datetime.now(
            datetime.timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

        with self._lock:
            self._tasks[task_id] = TaskInfo(
                task_id=task_id,
                filename=filename,
                operation=operation,
                created_at=now,
            )
        logger.info(f"任务已创建: {task_id} ({operation} - {filename})")
        return task_id

    def update_task(
        self,
        task_id: str,
        status: TaskStatus,
        progress: int,
        message: str = "",
        **extra,
    ) -> None:
        """更新任务状态并推送 SSE 事件。"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                logger.warning(f"更新不存在的任务: {task_id}")
                return
            task.status = status
            task.progress = progress
            task.message = message
            # 合并额外字段（如 output_path, employee_id）
            for k, v in extra.items():
                if hasattr(task, k):
                    setattr(task, k, v)
                else:
                    task.extra[k] = v
            # 任务完成/失败时记入历史
            if status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                self._history.append(HistoryItem(
                    task_id=task_id,
                    operation=task.operation,
                    filename=task.filename,
                    status=status.value,
                    employee_id=task.employee_id,
                    created_at=task.created_at,
                    message=message,
                ))

        # 推送 SSE 事件（在锁外执行，避免死锁）
        self._push_event(task_id, status, progress, message)

    def get_task(self, task_id: str) -> Optional[TaskResponse]:
        """获取任务状态。"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return None
            return TaskResponse(
                task_id=task.task_id,
                status=task.status,
                progress=task.progress,
                message=task.message,
                filename=task.filename,
                created_at=task.created_at,
            )

    def get_output_path(self, task_id: str) -> Optional[str]:
        """获取任务的输出文件路径。"""
        with self._lock:
            task = self._tasks.get(task_id)
            return task.output_path if task else None

    async def subscribe(self, task_id: str) -> AsyncGenerator[str, None]:
        """SSE 事件流生成器，格式: data: {json}\\n\\n。"""
        queue: asyncio.Queue = asyncio.Queue()
        with self._lock:
            if task_id not in self._events:
                self._events[task_id] = []
            self._events[task_id].append(queue)

        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
                    continue
                yield f"data: {event}\n\n"
                # 任务完成/失败时结束流
                data = json.loads(event)
                if data.get("status") in ("completed", "failed"):
                    break
        finally:
            with self._lock:
                queues = self._events.get(task_id, [])
                if queue in queues:
                    queues.remove(queue)

    def _push_event(
        self, task_id: str, status: TaskStatus, progress: int, message: str,
    ) -> None:
        """向所有订阅者推送事件。"""
        event_data = json.dumps({
            "task_id": task_id,
            "status": status.value,
            "progress": progress,
            "message": message,
        }, ensure_ascii=False)

        with self._lock:
            queues = self._events.get(task_id, [])
            for q in queues:
                try:
                    q.put_nowait(event_data)
                except asyncio.QueueFull:
                    logger.warning(f"SSE 队列已满: {task_id}")

    def get_history(
        self, page: int, page_size: int, operation: Optional[str] = None,
    ) -> tuple[list[HistoryItem], int]:
        """分页获取历史记录（最新在前）。"""
        with self._lock:
            items = self._history
            if operation:
                items = [i for i in items if i.operation == operation]
            total = len(items)
            items = list(reversed(items))
            start = (page - 1) * page_size
            end = start + page_size
            return items[start:end], total

    def cleanup_old_files(self, max_age_minutes: int = 30) -> None:
        """委托给 cleanup 模块执行文件清理。"""
        cleanup_old_files(max_age_minutes)
