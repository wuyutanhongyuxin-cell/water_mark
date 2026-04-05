"""
水印验证 API 路由。

提供单文件验证和批量验证端点。
验证操作为同步处理，在线程池中执行后直接返回结果。
"""

import asyncio

from fastapi import APIRouter, Form, HTTPException, UploadFile
from loguru import logger

from src.web.dependencies import save_upload
from src.web.schemas import VerifyBatchResponse, VerifyResponse
from src.web.services.extract_service import run_batch_verify, run_verify

router = APIRouter(prefix="/api", tags=["verify"])


@router.post("/verify", response_model=VerifyResponse)
async def verify_file_endpoint(
    file: UploadFile = None,
    expected_id: str = Form(""),
    strength: str = Form("medium"),
):
    """
    验证单个文件中的水印。

    可选提供 expected_id 进行员工 ID 匹配验证。
    不提供 expected_id 时仅检查是否存在水印。
    """
    if file is None:
        raise HTTPException(status_code=400, detail="请上传文件")

    input_path = await save_upload(file)

    # 在线程池中执行验证
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, run_verify, input_path, expected_id, strength,
    )

    # 清理上传文件
    try:
        input_path.unlink(missing_ok=True)
    except OSError:
        pass

    return result


@router.post("/verify/batch", response_model=VerifyBatchResponse)
async def verify_batch(
    files: list[UploadFile] = None,
    expected_id: str = Form(""),
    strength: str = Form("medium"),
):
    """
    批量验证多个文件中的水印。

    返回每个文件的验证结果，以及通过/总数统计。
    """
    if not files:
        raise HTTPException(status_code=400, detail="请上传至少一个文件")

    # 保存所有文件
    file_paths: list[tuple[str, any]] = []
    for file in files:
        try:
            saved_path = await save_upload(file)
            orig_name = file.filename or "unknown"
            file_paths.append((orig_name, saved_path))
        except HTTPException as e:
            logger.warning(f"批量验证跳过文件: {file.filename} - {e.detail}")

    if not file_paths:
        raise HTTPException(status_code=400, detail="没有有效的文件可验证")

    # 在线程池中执行批量验证
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, run_batch_verify, file_paths, expected_id, strength,
    )

    # 清理上传文件
    for _, path in file_paths:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass

    return result
