"""
审计日志模块。

记录所有水印操作（嵌入/提取/验证）的结构化审计日志。
使用 loguru 独立 sink，输出到 logs/audit.log。
审计失败不中断主流程（静默降级）。
"""

import json
import datetime
import threading
from pathlib import Path
from typing import Optional

from loguru import logger

# 懒加载状态：避免模块导入时就创建文件
_initialized = False
_audit_logger = None
_init_lock = threading.Lock()


def _ensure_init() -> None:
    """懒加载初始化审计日志 sink（仅首次调用时执行，线程安全）。"""
    global _audit_logger, _initialized
    if _initialized:
        return
    with _init_lock:
        if _initialized:  # double-check locking
            return
        try:
            # 延迟导入，避免循环依赖（audit ← router ← detector）
            from src.core.router import load_settings
            settings = load_settings()
            log_config = settings.get("logging", {})
            audit_file = log_config.get("audit_file", "logs/audit.log")
            rotation = log_config.get("rotation", "10 MB")

            # 确保日志目录存在
            audit_path = Path(audit_file)
            audit_path.parent.mkdir(parents=True, exist_ok=True)

            # 添加独立 sink：用 filter 隔离审计日志与普通日志
            _audit_logger = logger.bind(audit=True)
            logger.add(
                str(audit_path),
                filter=lambda record: record["extra"].get("audit"),
                format="{time:YYYY-MM-DD HH:mm:ss} | AUDIT | {message}",
                rotation=rotation,
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning(f"Audit logger init failed (non-fatal): {e}")
        # 无论成功失败都标记已初始化（避免无限重试，失败时 _audit_logger=None 静默降级）
        _initialized = True


def _write_audit(event_type: str, data: dict) -> None:
    """写入一条审计记录（JSON 格式）。审计失败静默降级。"""
    _ensure_init()
    if _audit_logger is None:
        return

    record = {
        "event": event_type,
        "timestamp": datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat(),
        **data,
    }
    try:
        _audit_logger.info(json.dumps(record, ensure_ascii=False))
    except Exception:
        pass  # 审计失败不中断主流程


def log_embed(
    file_path: str,
    employee_id: str,
    success: bool,
    output_path: Optional[str] = None,
    message: str = "",
) -> None:
    """记录水印嵌入操作。"""
    _write_audit("embed", {
        "file": file_path,
        "employee_id": employee_id,
        "success": success,
        "output": output_path or "",
        "message": message,
    })


def log_extract(
    file_path: str,
    success: bool,
    employee_id: str = "",
    message: str = "",
) -> None:
    """记录水印提取操作。"""
    _write_audit("extract", {
        "file": file_path,
        "success": success,
        "employee_id": employee_id,
        "message": message,
    })


def log_verify(
    file_path: str,
    success: bool,
    expected_employee_id: str = "",
    message: str = "",
) -> None:
    """记录水印验证操作。"""
    _write_audit("verify", {
        "file": file_path,
        "success": success,
        "expected_employee_id": expected_employee_id,
        "message": message,
    })


def log_ai_call(
    operation: str,
    model: str,
    input_summary: str,
    output_summary: str,
    tokens: int = 0,
    latency: float = 0.0,
    success: bool = True,
) -> None:
    """记录 AI API 调用操作。"""
    _write_audit("ai_call", {
        "operation": operation,
        "model": model,
        "input_summary": input_summary,
        "output_summary": output_summary,
        "tokens": tokens,
        "latency_s": round(latency, 3),
        "success": success,
    })
