"""
水印提取 API 路由。

提供单文件水印提取端点。
提取操作为同步处理（通常较快），在线程池中执行后直接返回结果。
"""

import asyncio

from fastapi import APIRouter, Form, HTTPException, UploadFile
from loguru import logger

from src.web.dependencies import save_upload
from src.web.schemas import ExtractResponse
from src.web.services.extract_service import run_extract

router = APIRouter(prefix="/api", tags=["extract"])


@router.post("/extract", response_model=ExtractResponse)
async def extract_file(
    file: UploadFile = None,
    strength: str = Form("medium"),
):
    """
    提取文件中的水印信息。

    同步处理：上传文件 -> 提取水印 -> 返回结果。
    不创建异步任务，直接返回提取结果。
    """
    if file is None:
        raise HTTPException(status_code=400, detail="请上传文件")

    # 保存上传文件
    input_path = await save_upload(file)

    # 在线程池中执行提取（防止阻塞事件循环）
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, run_extract, input_path, strength,
    )

    # 提取完成后清理上传文件（非必须，守护线程也会清理）
    try:
        input_path.unlink(missing_ok=True)
    except OSError:
        pass

    return result
