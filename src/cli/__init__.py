"""
CLI 共享工具模块。

提供颜色输出、结果格式化、强度解析等 CLI 通用功能。
所有命令文件共享此模块，避免重复代码。
"""

import json
import time
from typing import Optional

import click

from src.core.router import load_settings
from src.watermarks.base import (
    EmbedResult, ExtractResult, WatermarkStrength,
)
from src.core.verifier import VerifyResult


# ========== 颜色输出工具 ==========

def ok(msg: str) -> None:
    """输出成功信息（绿色 ✓）。"""
    click.echo(click.style(f"  [OK] {msg}", fg="green"))


def fail(msg: str) -> None:
    """输出失败信息（红色 ✗）。"""
    click.echo(click.style(f"  [FAIL] {msg}", fg="red"))


def warn(msg: str) -> None:
    """输出警告信息（黄色 !）。"""
    click.echo(click.style(f"  [WARN] {msg}", fg="yellow"))


def info(msg: str) -> None:
    """输出提示信息（蓝色 i）。"""
    click.echo(click.style(f"  [INFO] {msg}", fg="blue"))


# ========== 强度解析 ==========

def resolve_strength(s: Optional[str]) -> WatermarkStrength:
    """
    解析强度参数。None 时从 settings.yaml 读取默认值。

    Args:
        s: "low" / "medium" / "high" 或 None

    Returns:
        WatermarkStrength 枚举值
    """
    if s is not None:
        return WatermarkStrength(s)
    settings = load_settings()
    default = settings.get("watermark", {}).get("default_strength", "medium")
    return WatermarkStrength(default)


# ========== 自定义元数据解析 ==========

def parse_custom_data(tuples: tuple) -> dict:
    """
    解析 key=value 格式的自定义元数据。

    Args:
        tuples: Click 收集的多值元组，如 ("dept=Finance", "level=3")

    Returns:
        dict: {"dept": "Finance", "level": "3"}
    """
    result = {}
    for item in tuples:
        if "=" not in item:
            warn(f"Ignored invalid custom data (missing '='): {item}")
            continue
        key, value = item.split("=", 1)
        result[key.strip()] = value.strip()
    return result


# ========== 结果格式化 ==========

def format_embed_result(result: EmbedResult, filename: str) -> None:
    """格式化输出嵌入结果。"""
    if result.success:
        ok(f"{filename} -> {result.output_path}")
        if result.quality_metrics:
            metrics = ", ".join(
                f"{k}={v:.2f}" if isinstance(v, float) else f"{k}={v}"
                for k, v in result.quality_metrics.items()
            )
            info(f"Quality: {metrics}")
        info(f"Time: {result.elapsed_time:.2f}s")
    else:
        fail(f"{filename}: {result.message}")


def format_extract_result(
    result: ExtractResult, filename: str, json_mode: bool = False,
) -> None:
    """格式化输出提取结果。"""
    if json_mode:
        data = {
            "file": filename,
            "success": result.success,
            "employee_id": result.payload.employee_id if result.payload else None,
            "timestamp": result.payload.timestamp if result.payload else None,
            "confidence": result.confidence,
            "message": result.message,
        }
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
        return
    if result.success and result.payload:
        ok(f"{filename}")
        info(f"Employee: {result.payload.employee_id}")
        info(f"Timestamp: {result.payload.timestamp}")
        info(f"Confidence: {result.confidence:.2f}")
        if result.payload.custom_data:
            info(f"Custom: {result.payload.custom_data}")
    else:
        fail(f"{filename}: {result.message}")


def format_verify_result(result: VerifyResult, json_mode: bool = False) -> None:
    """格式化输出验证结果。"""
    fname = result.file_path.name
    if json_mode:
        data = {
            "file": str(result.file_path),
            "success": result.success,
            "employee_id": result.employee_id,
            "matched": result.matched,
            "message": result.message,
        }
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
        return
    if result.success and result.matched:
        ok(f"{fname}: {result.message}")
    elif result.success and not result.matched:
        warn(f"{fname}: {result.message}")
    else:
        fail(f"{fname}: {result.message}")


def format_batch_summary(
    total: int, success: int, failed: int, skipped: int, elapsed: float,
) -> None:
    """格式化输出批量处理汇总。"""
    click.echo("")
    click.echo(click.style("=" * 50, fg="cyan"))
    click.echo(click.style("  Batch Summary", fg="cyan", bold=True))
    click.echo(click.style("=" * 50, fg="cyan"))
    click.echo(f"  Total:   {total}")
    click.echo(click.style(f"  Success: {success}", fg="green"))
    if failed > 0:
        click.echo(click.style(f"  Failed:  {failed}", fg="red"))
    else:
        click.echo(f"  Failed:  {failed}")
    if skipped > 0:
        click.echo(click.style(f"  Skipped: {skipped}", fg="yellow"))
    else:
        click.echo(f"  Skipped: {skipped}")
    click.echo(f"  Time:    {elapsed:.2f}s")
    click.echo(click.style("=" * 50, fg="cyan"))
