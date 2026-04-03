"""
统一水印提取接口。

对外暴露 extract_watermark() 单一入口，内部完成：
文件检测 → 策略路由 → 提取水印 → 返回载荷
"""

from pathlib import Path
from typing import Optional
import logging

from src.core.router import route_file
from src.watermarks.base import ExtractResult, WatermarkStrength

logger = logging.getLogger(__name__)


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

    # 1. 路由匹配
    route = route_file(file_path, strength=strength)
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
        logger.error(f"Extract failed for {file_path}: {e}")
        return ExtractResult(
            success=False,
            message=f"Extract error: {e}",
        )

    if result.success:
        logger.info(
            f"Extracted watermark from {file_path.name} "
            f"(confidence={result.confidence:.2f})"
        )
    else:
        logger.warning(f"No watermark found in {file_path.name}")

    return result


def verify_watermark(
    file_path: Path,
    expected_employee_id: str,
    strength: WatermarkStrength = WatermarkStrength.MEDIUM,
) -> bool:
    """
    验证文件中是否包含指定员工的水印。

    简化版验证：只比对 employee_id。

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
