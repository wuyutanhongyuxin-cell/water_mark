"""
水印验证模块。

提供独立的水印验证接口，基于 extractor 提取后比对。
支持单文件验证和批量验证。
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from loguru import logger

from src.core.extractor import extract_watermark
from src.security.audit import log_verify
from src.watermarks.base import WatermarkStrength


@dataclass
class VerifyResult:
    """
    验证结果。

    Attributes:
        success: 是否成功提取到水印（True=提取成功，不代表 ID 匹配）
        file_path: 被验证的文件路径
        employee_id: 提取到的员工 ID
        matched: 与预期 ID 是否匹配（未提供预期 ID 时默认 True 表示"无不匹配"）
        message: 结果描述

    注意：success=True 且 matched=False 表示"成功提取水印但 ID 不一致"。
    若需判断验证是否完全通过，应检查 success and matched。
    """
    success: bool
    file_path: Path
    employee_id: str = ""
    matched: bool = False
    message: str = ""


def verify_file(
    file_path: Path,
    expected_employee_id: Optional[str] = None,
    strength: WatermarkStrength = WatermarkStrength.MEDIUM,
) -> VerifyResult:
    """
    验证文件中是否包含有效水印。

    如果提供 expected_employee_id，还会比对员工 ID 是否一致。

    Args:
        file_path: 待验证文件路径
        expected_employee_id: 预期员工 ID（可选，None 表示只验证有无水印）
        strength: 水印强度（需与嵌入时一致）

    Returns:
        VerifyResult: 验证结果
    """
    file_path = Path(file_path)

    # 提取水印
    result = extract_watermark(file_path, strength=strength)

    if not result.success or result.payload is None:
        log_verify(
            str(file_path), success=False,
            expected_employee_id=expected_employee_id or "",
            message="No watermark found",
        )
        return VerifyResult(
            success=False, file_path=file_path,
            message=f"No watermark found: {result.message}",
        )

    found_id = result.payload.employee_id

    # 需要比对 employee_id
    if expected_employee_id is not None:
        matched = found_id == expected_employee_id
        msg = (
            f"Matched: {found_id}" if matched
            else f"Mismatch: expected={expected_employee_id}, found={found_id}"
        )
        log_verify(
            str(file_path), success=matched,
            expected_employee_id=expected_employee_id, message=msg,
        )
        return VerifyResult(
            success=True, file_path=file_path,
            employee_id=found_id, matched=matched, message=msg,
        )

    # 只验证有无水印（不比对 ID）
    log_verify(str(file_path), success=True, message=f"Found: {found_id}")
    return VerifyResult(
        success=True, file_path=file_path,
        employee_id=found_id, matched=True,
        message=f"Found watermark: {found_id}",
    )


def batch_verify(
    file_paths: list[Path],
    expected_employee_id: Optional[str] = None,
    strength: WatermarkStrength = WatermarkStrength.MEDIUM,
) -> list[VerifyResult]:
    """
    批量验证多个文件。

    Args:
        file_paths: 文件路径列表
        expected_employee_id: 预期员工 ID（可选）
        strength: 水印强度

    Returns:
        list[VerifyResult]: 验证结果列表
    """
    results = []
    for fp in file_paths:
        try:
            r = verify_file(fp, expected_employee_id, strength)
        except Exception as e:
            logger.warning(f"Verify error for {fp}: {e}")
            log_verify(str(fp), success=False, message=f"Exception: {e}")
            r = VerifyResult(
                success=False, file_path=Path(fp),
                message=f"Verification error: {e}",
            )
        results.append(r)
    return results
