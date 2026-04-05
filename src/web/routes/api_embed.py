"""
水印嵌入 API 路由。

提供单文件嵌入、批量嵌入、文件下载三个端点。
嵌入操作为异步任务，立即返回 task_id，客户端通过 SSE 获取进度。
"""

import asyncio
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from loguru import logger

from src.web.dependencies import get_output_dir, save_upload
from src.web.schemas import EmbedResponse
from src.web.services.embed_service import run_embed

router = APIRouter(prefix="/api", tags=["embed"])


def _get_task_manager(request: Request):
    """从 app.state 获取任务管理器。"""
    return request.app.state.task_manager


@router.post("/embed", response_model=EmbedResponse)
async def embed_file(
    request: Request,
    file: UploadFile = None,
    employee_id: str = Form(...),
    strength: str = Form("medium"),
    auto_verify: bool = Form(True),
):
    """
    嵌入水印（单文件）。

    接受文件上传和参数，创建异步任务，立即返回 task_id。
    嵌入进度通过 /api/tasks/{task_id}/events (SSE) 获取。
    """
    if file is None:
        raise HTTPException(status_code=400, detail="请上传文件")

    # 保存上传文件
    input_path = await save_upload(file)
    filename = file.filename or "unknown"

    # 创建任务
    tm = _get_task_manager(request)
    task_id = tm.create_task(filename, "embed")
    output_dir = get_output_dir()

    # 在线程池中异步执行嵌入（fire-and-forget）
    loop = asyncio.get_event_loop()
    loop.run_in_executor(
        None, run_embed,
        tm, task_id, input_path, employee_id,
        strength, auto_verify, output_dir,
    )

    return EmbedResponse(task_id=task_id, message="任务已创建，正在处理中")


@router.post("/embed/batch", response_model=list[EmbedResponse])
async def embed_batch(
    request: Request,
    files: list[UploadFile] = None,
    employee_id: str = Form(...),
    strength: str = Form("medium"),
    auto_verify: bool = Form(True),
):
    """
    批量嵌入水印（多文件）。

    为每个文件创建独立的异步任务，返回所有 task_id。
    """
    if not files:
        raise HTTPException(status_code=400, detail="请上传至少一个文件")

    tm = _get_task_manager(request)
    output_dir = get_output_dir()
    loop = asyncio.get_event_loop()
    responses = []

    for file in files:
        try:
            input_path = await save_upload(file)
            filename = file.filename or "unknown"
            task_id = tm.create_task(filename, "embed")

            # 为每个文件启动独立的后台任务
            loop.run_in_executor(
                None, run_embed,
                tm, task_id, input_path, employee_id,
                strength, auto_verify, output_dir,
            )
            responses.append(EmbedResponse(
                task_id=task_id, message=f"任务已创建: {filename}",
            ))
        except HTTPException as e:
            # 单个文件校验失败不影响其他文件
            responses.append(EmbedResponse(
                task_id="", message=f"文件 {file.filename} 失败: {e.detail}",
            ))
            logger.warning(f"批量嵌入跳过文件: {file.filename} - {e.detail}")

    return responses


@router.get("/embed/{task_id}/download")
async def download_file(request: Request, task_id: str):
    """
    下载嵌入水印后的文件。

    仅当任务状态为 completed 时可下载。
    """
    tm = _get_task_manager(request)
    task = tm.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"任务未完成，当前状态: {task.status}",
        )

    output_path_str = tm.get_output_path(task_id)
    if not output_path_str:
        raise HTTPException(status_code=404, detail="输出文件路径为空")

    output_path = Path(output_path_str)
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="输出文件已被清理")

    return FileResponse(
        path=str(output_path),
        filename=output_path.name,
        media_type="application/octet-stream",
    )
