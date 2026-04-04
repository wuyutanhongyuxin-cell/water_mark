"""
文件类型检测模块（双重验证：magic bytes + 扩展名）。
一致 → 确认；不一致 → 以 magic bytes 为准 + 告警。
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from loguru import logger

# 文件类型分类映射：MIME 前缀/模式 → 内部类别
FILE_CATEGORIES = {
    "image": [
        "image/jpeg", "image/png", "image/bmp",
        "image/tiff", "image/webp", "image/gif",
    ],
    "pdf": ["application/pdf"],
    "office_word": [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ],
    "office_excel": [
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ],
    "office_pptx": [
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ],
    "audio": [
        "audio/mpeg", "audio/wav", "audio/x-wav",
        "audio/flac", "audio/ogg",
    ],
    "video": [
        "video/mp4", "video/x-msvideo", "video/x-matroska",
        "video/quicktime", "video/webm",
    ],
    "text": [
        "text/plain", "text/csv", "text/html",
        "application/json", "text/markdown",
    ],
}

# 扩展名 → 预期 MIME 类型（常见映射）
EXT_TO_MIME = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".png": "image/png", ".bmp": "image/bmp",
    ".tiff": "image/tiff", ".tif": "image/tiff",
    ".webp": "image/webp", ".gif": "image/gif",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".mp3": "audio/mpeg", ".wav": "audio/wav",
    ".flac": "audio/flac", ".ogg": "audio/ogg",
    ".mp4": "video/mp4", ".avi": "video/x-msvideo",
    ".mkv": "video/x-matroska", ".mov": "video/quicktime",
    ".txt": "text/plain", ".csv": "text/csv",
    ".json": "application/json", ".md": "text/markdown",
}


@dataclass
class DetectionResult:
    """
    文件类型检测结果。

    Attributes:
        mime_type: 最终确定的 MIME 类型
        category: 内部类别（image/pdf/office_word/...）
        extension: 文件扩展名
        confidence: 检测置信度（both_match=1.0, magic_only=0.8, ext_only=0.5）
        warning: 不一致时的告警信息
    """
    mime_type: str
    category: str
    extension: str
    confidence: float = 1.0
    warning: str = ""


def _detect_by_magic(file_path: Path) -> Optional[str]:
    """通过 magic bytes 检测 MIME。读取文件头后检测，避免中文路径问题。"""
    # 先读取文件头 8KB（绕过 python-magic 不支持中文路径的 bug）
    try:
        header = file_path.read_bytes()[:8192]
    except OSError as e:
        logger.warning(f"Cannot read file header: {e}")
        return None

    # 方案1：python-magic-bin（使用 from_buffer 避免路径编码问题）
    try:
        import magic
        mime = magic.from_buffer(header, mime=True)
        if mime:
            return mime
    except ImportError:
        logger.debug("python-magic-bin not installed, falling back to filetype")
    except Exception as e:
        logger.warning(f"magic detection failed: {e}")

    # 方案2：filetype（直接传入 bytes，同样避免路径问题）
    try:
        import filetype
        kind = filetype.guess(header)
        if kind is not None:
            return kind.mime
    except ImportError:
        logger.warning("filetype not installed")
    except Exception as e:
        logger.warning(f"filetype detection failed: {e}")

    return None


def _detect_by_extension(file_path: Path) -> Optional[str]:
    """通过文件扩展名推断 MIME 类型。"""
    ext = file_path.suffix.lower()
    return EXT_TO_MIME.get(ext)


def _mime_to_category(mime_type: str) -> Optional[str]:
    """将 MIME 类型映射为内部文件类别。清洗 MIME 参数（如 charset）。"""
    # 清洗 MIME 参数：text/plain; charset=utf-8 → text/plain
    clean_mime = mime_type.split(";")[0].strip()
    for category, mimes in FILE_CATEGORIES.items():
        if clean_mime in mimes:
            return category
    return None


def detect_file_type(file_path: Path) -> DetectionResult:
    """检测文件类型（magic bytes + 扩展名双重验证）。Raises FileNotFoundError。"""
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = file_path.suffix.lower()
    magic_mime = _detect_by_magic(file_path)
    ext_mime = _detect_by_extension(file_path)

    # OOXML 特判：.docx/.xlsx/.pptx 的 magic bytes 是 ZIP 容器
    # python-magic 可能返回 application/zip 而非 OOXML MIME
    if magic_mime and magic_mime.split(";")[0].strip() in (
        "application/zip", "application/x-zip-compressed",
    ):
        if ext in EXT_TO_MIME and ext in (".docx", ".xlsx", ".pptx"):
            # 信任扩展名对应的 OOXML MIME（ZIP 是合法容器格式）
            magic_mime = EXT_TO_MIME[ext]
            logger.info(f"OOXML override: {ext} detected as ZIP, using {magic_mime}")

    # 清洗 MIME 参数
    if magic_mime:
        magic_mime = magic_mime.split(";")[0].strip()

    # 情况1：两者都成功且一致
    if magic_mime and ext_mime and magic_mime == ext_mime:
        category = _mime_to_category(magic_mime) or "unknown"
        return DetectionResult(
            mime_type=magic_mime, category=category,
            extension=ext, confidence=1.0,
        )

    # 情况2：两者都成功但不一致 → 以 magic 为准
    if magic_mime and ext_mime and magic_mime != ext_mime:
        category = _mime_to_category(magic_mime) or "unknown"
        warning = (
            f"MIME mismatch: magic={magic_mime}, ext={ext_mime}. "
            f"Using magic bytes result."
        )
        logger.warning(warning)
        return DetectionResult(
            mime_type=magic_mime, category=category,
            extension=ext, confidence=0.8, warning=warning,
        )

    # 情况3：只有 magic 成功
    if magic_mime:
        category = _mime_to_category(magic_mime) or "unknown"
        return DetectionResult(
            mime_type=magic_mime, category=category,
            extension=ext, confidence=0.8,
        )

    # 情况4：只有扩展名成功
    if ext_mime:
        category = _mime_to_category(ext_mime) or "unknown"
        warning = "Detection based on extension only (no magic bytes match)"
        logger.warning(warning)
        return DetectionResult(
            mime_type=ext_mime, category=category,
            extension=ext, confidence=0.5, warning=warning,
        )

    # 情况5：都失败
    return DetectionResult(
        mime_type="application/octet-stream", category="unknown",
        extension=ext, confidence=0.0,
        warning="Unable to detect file type",
    )
