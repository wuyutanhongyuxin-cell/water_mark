"""
统一水印提取接口。

对外暴露 extract_watermark() 单一入口，内部完成：
文件检测 → 策略路由 → 提取水印 → 返回载荷
"""

from pathlib import Path

from loguru import logger

from src.core.router import route_file, load_settings
from src.security.audit import log_extract
from src.watermarks.base import ExtractResult, WatermarkStrength


def extract_watermark(
    file_path: Path,
    strength: WatermarkStrength = WatermarkStrength.MEDIUM,
) -> ExtractResult:
    """
    提取水印的统一入口。

    流程：
    1. 检测文件类型 → 匹配处理器
    2. 调用处理器的 extract() 方法
    3. 返回提取结果（含载荷、置信度）

    Args:
        file_path: 待提取水印的文件路径
        strength: 水印强度（需与嵌入时一致）

    Returns:
        ExtractResult: 提取结果
    """
    file_path = Path(file_path)

    # 0. 文件存在性检查（统一返回 Result，不抛异常）
    if not file_path.exists():
        return ExtractResult(success=False, message=f"File not found: {file_path}")
    if not file_path.is_file():
        return ExtractResult(success=False, message=f"Not a file: {file_path}")

    # 0.1 文件大小检查（与 embedder 对齐，防 DoS）
    settings = load_settings()
    max_mb = settings.get("watermark", {}).get("max_file_size_mb", 500)
    try:
        size_mb = file_path.stat().st_size / (1024 * 1024)
    except OSError:
        return ExtractResult(success=False, message=f"Cannot stat file: {file_path}")
    if size_mb > max_mb:
        return ExtractResult(
            success=False,
            message=f"File too large: {size_mb:.1f}MB > {max_mb}MB limit",
        )

    # 1. 路由匹配
    try:
        route = route_file(file_path, strength=strength)
    except Exception as e:
        return ExtractResult(success=False, message=f"Routing error: {e}")
    if route.processor is None:
        return ExtractResult(
            success=False,
            message=f"Routing failed: {route.error}",
        )

    # 2. 文件预检查
    if not route.processor.validate_file(file_path):
        return ExtractResult(
            success=False,
            message=f"File validation failed: {file_path}",
        )

    # 3. 执行提取
    try:
        result = route.processor.extract(file_path)
    except Exception as e:
        logger.exception(f"Extract failed for {file_path}: {e}")
        log_extract(str(file_path), False, message=str(e))
        return ExtractResult(
            success=False,
            message=f"Extract error: {e}",
        )

    # AI 异常检测（opt-in, graceful degradation）
    # NOTE: 延迟导入 src.ai 以避免循环依赖：extractor → ai.anomaly → watermarks.base
    try:
        from src.ai import detect_anomaly
        _anomaly = detect_anomaly(result, file_name=file_path.name)
        if _anomaly.has_anomaly:
            logger.warning(
                f"Anomaly: {file_path.name} - "
                f"{_anomaly.anomaly_type} ({_anomaly.risk_level})"
            )
    except Exception as _ai_err:
        logger.warning(f"AI anomaly detection failed (non-fatal): {type(_ai_err).__name__}")

    if result.success:
        emp_id = result.payload.employee_id if result.payload else ""
        log_extract(str(file_path), True, employee_id=emp_id)
        logger.info(
            f"Extracted watermark from {file_path.name} "
            f"(confidence={result.confidence:.2f})"
        )
    else:
        log_extract(str(file_path), False, message=result.message)
        logger.warning(f"No watermark found in {file_path.name}")

    return result


def verify_watermark(
    file_path: Path,
    expected_employee_id: str,
    strength: WatermarkStrength = WatermarkStrength.MEDIUM,
) -> bool:
    """
    验证文件中是否包含指定员工的水印（仅比对 employee_id）。

    注意：仅做身份验证。如需完整性验证（含时间戳），请直接调用
    processor.verify()。

    Args:
        file_path: 待验证文件
        expected_employee_id: 预期的员工 ID
        strength: 水印强度

    Returns:
        bool: 验证通过返回 True
    """
    result = extract_watermark(file_path, strength=strength)
    if not result.success or result.payload is None:
        return False
    return result.payload.employee_id == expected_employee_id
