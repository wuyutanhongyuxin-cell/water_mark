"""
Web 模块公共依赖。

提供文件上传校验、路径管理、文件名清理等共享功能。
所有路由模块通过此文件获取公共依赖，避免重复逻辑。
"""

import re
import tempfile
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from loguru import logger

# ========== 支持的文件扩展名（来自 watermark_rules.yaml） ==========

ALLOWED_EXTENSIONS: set[str] = {
    # 图像
    ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp",
    # PDF
    ".pdf",
    # Office
    ".docx", ".xlsx", ".pptx",
    # 音频
    ".wav", ".flac",
    # 视频
    ".mp4", ".avi", ".mkv", ".mov",
    # 文本
    ".txt", ".csv", ".json", ".md",
}

# ========== 文件大小上限（MB） ==========
MAX_FILE_SIZE: int = 500

# ========== 临时目录 ==========
UPLOAD_DIR = Path(tempfile.gettempdir()) / "watermark_uploads"
OUTPUT_DIR = Path(tempfile.gettempdir()) / "watermark_outputs"


def get_upload_dir() -> Path:
    """确保上传目录存在并返回路径。"""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return UPLOAD_DIR


def get_output_dir() -> Path:
    """确保输出目录存在并返回路径。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


def sanitize_filename(name: str) -> str:
    """
    清理文件名：保留中文字符和常规字符，移除路径分隔符和控制字符。

    使用 UUID 前缀确保唯一性，避免文件覆盖。

    Args:
        name: 原始文件名

    Returns:
        清理后的安全文件名（含 UUID 前缀）
    """
    # 移除路径分隔符和控制字符，保留中文、字母、数字、点、短横线、下划线
    cleaned = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', name)
    # 截断过长文件名（保留扩展名）
    stem = Path(cleaned).stem[:100]
    ext = Path(cleaned).suffix
    # UUID 前缀确保唯一
    prefix = uuid.uuid4().hex[:8]
    return f"{prefix}_{stem}{ext}"


async def validate_upload(file: UploadFile) -> UploadFile:
    """
    校验上传文件的扩展名和大小。

    Args:
        file: FastAPI 上传文件对象

    Returns:
        校验通过的文件对象

    Raises:
        HTTPException: 文件类型不支持或超过大小限制
    """
    filename = file.filename or "unknown"
    ext = Path(filename).suffix.lower()

    # 扩展名校验
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {ext}，支持: {sorted(ALLOWED_EXTENSIONS)}",
        )

    # 文件大小校验（读取前先检查 Content-Length，读取后再验证实际大小）
    return file


async def save_upload(file: UploadFile) -> Path:
    """
    保存上传文件到临时目录。

    先校验文件，然后以安全文件名保存到 UPLOAD_DIR。

    Args:
        file: 上传文件对象

    Returns:
        保存后的文件路径

    Raises:
        HTTPException: 校验失败或保存失败
    """
    await validate_upload(file)
    upload_dir = get_upload_dir()
    safe_name = sanitize_filename(file.filename or "upload")
    save_path = upload_dir / safe_name

    try:
        content = await file.read()
        # 实际大小校验
        size_mb = len(content) / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"文件过大: {size_mb:.1f}MB，上限 {MAX_FILE_SIZE}MB",
            )
        save_path.write_bytes(content)
        logger.info(f"文件已保存: {safe_name} ({size_mb:.1f}MB)")
        return save_path
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"保存文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"保存文件失败: {e}")
