"""
任务状态与系统配置 API 路由。

提供任务查询、SSE 事件流、历史记录、系统配置等端点。
注意：history 端点必须在 {task_id} 之前注册，避免路径冲突。
"""

import json

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from loguru import logger

from src.web.dependencies import ALLOWED_EXTENSIONS, MAX_FILE_SIZE
from src.web.schemas import (
    ConfigResponse,
    HistoryResponse,
    TaskResponse,
)

router = APIRouter(prefix="/api", tags=["tasks"])


@router.get("/config", response_model=ConfigResponse)
async def get_config():
    """获取系统支持的配置信息（扩展名、大小限制、强度选项）。"""
    return ConfigResponse(
        supported_extensions=sorted(ALLOWED_EXTENSIONS),
        max_file_size_mb=MAX_FILE_SIZE,
        strengths=["low", "medium", "high"],
    )


@router.get("/tasks/history", response_model=HistoryResponse)
async def get_history(
    request: Request,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    operation: str = Query("", description="操作类型过滤: embed/extract/verify"),
):
    """
    分页获取操作历史。

    支持按操作类型过滤。最新记录排在最前。
    注意：此端点路径必须在 /tasks/{task_id} 之前注册。
    """
    tm = request.app.state.task_manager
    op_filter = operation if operation else None
    items, total = tm.get_history(page, page_size, op_filter)

    return HistoryResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(request: Request, task_id: str):
    """获取指定任务的当前状态。"""
    tm = request.app.state.task_manager
    task = tm.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    return task


@router.get("/tasks/{task_id}/events")
async def task_events(request: Request, task_id: str):
    """
    SSE 事件流端点。

    客户端通过 EventSource 连接此端点，实时获取任务进度更新。
    事件格式: data: {"task_id": "...", "status": "...", "progress": N}\n\n

    任务完成或失败后自动关闭连接。
    """
    tm = request.app.state.task_manager
    task = tm.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    # 如果任务已完成/失败，直接返回最终状态
    if task.status in ("completed", "failed"):
        final_event = json.dumps({
            "task_id": task.task_id,
            "status": task.status,
            "progress": task.progress,
            "message": task.message,
        }, ensure_ascii=False)

        async def _single_event():
            yield f"data: {final_event}\n\n"

        return StreamingResponse(
            _single_event(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # 订阅实时事件流
    return StreamingResponse(
        tm.subscribe(task_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
