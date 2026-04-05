"""
水印提取与验证服务。

封装核心提取/验证逻辑，供 Web 路由调用。
所有函数为同步函数，通过 run_in_executor 在线程池中执行。
"""

from pathlib import Path
from typing import Optional

from loguru import logger

from src.core.extractor import extract_watermark
from src.core.verifier import verify_file, batch_verify
from src.watermarks.base import WatermarkStrength
from src.web.schemas import (
    ExtractResponse,
    VerifyBatchItem,
    VerifyBatchResponse,
    VerifyResponse,
)


def _parse_strength(strength: str) -> WatermarkStrength:
    """将字符串转为 WatermarkStrength 枚举，无效值回退 MEDIUM。"""
    try:
        return WatermarkStrength(strength.lower())
    except ValueError:
        logger.warning(f"无效的水印强度 '{strength}'，使用默认值 medium")
        return WatermarkStrength.MEDIUM


def run_extract(file_path: Path, strength: str) -> ExtractResponse:
    """
    同步提取水印，直接返回结果。

    Args:
        file_path: 待提取文件路径
        strength: 水印强度字符串

    Returns:
        ExtractResponse: 提取结果
    """
    try:
        wm_strength = _parse_strength(strength)
        result = extract_watermark(file_path, strength=wm_strength)

        if result.success and result.payload:
            return ExtractResponse(
                success=True,
                employee_id=result.payload.employee_id,
                timestamp=result.payload.timestamp,
                confidence=result.confidence,
                message="水印提取成功",
            )
        return ExtractResponse(
            success=False,
            message=result.message or "未找到水印",
        )
    except Exception as e:
        logger.exception(f"提取异常: {e}")
        return ExtractResponse(success=False, message=f"提取异常: {e}")


def run_verify(
    file_path: Path, expected_id: Optional[str], strength: str,
) -> VerifyResponse:
    """
    同步验证单个文件。

    Args:
        file_path: 待验证文件路径
        expected_id: 预期员工 ID（空字符串视为 None）
        strength: 水印强度字符串

    Returns:
        VerifyResponse: 验证结果
    """
    try:
        wm_strength = _parse_strength(strength)
        # 空字符串转 None（不比对 ID）
        exp_id = expected_id if expected_id else None
        result = verify_file(file_path, exp_id, strength=wm_strength)

        return VerifyResponse(
            success=result.success,
            employee_id=result.employee_id,
            matched=result.matched,
            message=result.message,
        )
    except Exception as e:
        logger.exception(f"验证异常: {e}")
        return VerifyResponse(success=False, message=f"验证异常: {e}")


def run_batch_verify(
    file_paths: list[tuple[str, Path]],
    expected_id: Optional[str],
    strength: str,
) -> VerifyBatchResponse:
    """
    同步批量验证多个文件。

    Args:
        file_paths: [(原始文件名, 保存路径), ...] 列表
        expected_id: 预期员工 ID（空字符串视为 None）
        strength: 水印强度字符串

    Returns:
        VerifyBatchResponse: 批量验证结果
    """
    try:
        wm_strength = _parse_strength(strength)
        exp_id = expected_id if expected_id else None
        paths = [fp for _, fp in file_paths]
        results = batch_verify(paths, exp_id, strength=wm_strength)

        items = []
        passed = 0
        for (orig_name, _), result in zip(file_paths, results):
            item = VerifyBatchItem(
                filename=orig_name,
                success=result.success,
                employee_id=result.employee_id,
                matched=result.matched,
                message=result.message,
            )
            items.append(item)
            if result.success and result.matched:
                passed += 1

        return VerifyBatchResponse(
            results=items,
            total=len(items),
            passed=passed,
        )
    except Exception as e:
        logger.exception(f"批量验证异常: {e}")
        return VerifyBatchResponse(results=[], total=0, passed=0)
