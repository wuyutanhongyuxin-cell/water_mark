"""
verify 命令 — 验证文件中的水印。

支持单文件验证和目录批量验证。
可指定预期员工 ID 进行比对，或仅检测水印存在性。
"""

import json
import time
from pathlib import Path
from typing import Optional

import click

from src.cli import (
    ok, fail, info, warn,
    resolve_strength,
    format_verify_result,
    format_batch_summary,
)
from src.cli.scan import scan_directory, scan_summary
from src.core.verifier import verify_file, batch_verify, VerifyResult


@click.command()
@click.option("-i", "--input", "input_path", required=True,
              type=click.Path(exists=True),
              help="File or directory to verify")
@click.option("-e", "--employee", default=None,
              help="Expected employee ID (optional)")
@click.option("-s", "--strength", default=None,
              type=click.Choice(["low", "medium", "high"]),
              help="Watermark strength (default: from config)")
@click.option("-r", "--recursive", is_flag=True, default=False,
              help="Recursively scan directory")
@click.option("--json", "json_mode", is_flag=True, default=False,
              help="Output in JSON format")
def verify(input_path, employee, strength, recursive, json_mode):
    """Verify watermark in file(s)."""
    wm_strength = resolve_strength(strength)
    target = Path(input_path)

    # 单文件模式
    if target.is_file():
        _verify_single(target, employee, wm_strength, json_mode)
        return

    # 目录模式
    if target.is_dir():
        _verify_directory(target, employee, wm_strength, recursive, json_mode)
        return

    fail(f"Invalid path: {input_path}")
    raise SystemExit(2)


def _verify_single(
    file_path: Path,
    employee: Optional[str],
    strength,
    json_mode: bool,
) -> None:
    """单文件验证。"""
    if not json_mode:
        click.echo(f"\n  Verifying: {file_path.name}")

    result = verify_file(file_path, employee, strength)

    if json_mode:
        format_verify_result(result, json_mode=True)
    else:
        format_verify_result(result)

    # 退出码
    if not result.success:
        raise SystemExit(2)
    if not result.matched:
        raise SystemExit(1)
    raise SystemExit(0)


def _verify_directory(
    dir_path: Path,
    employee: Optional[str],
    strength,
    recursive: bool,
    json_mode: bool,
) -> None:
    """目录批量验证。"""
    start = time.monotonic()

    # 扫描目录
    files = scan_directory(dir_path, recursive=recursive)
    if not files:
        warn("No supported files found in directory")
        raise SystemExit(0)

    if not json_mode:
        summary = scan_summary(files)
        click.echo(f"\n  Found {len(files)} files to verify")
        for cat, cnt in sorted(summary.items()):
            info(f"{cat}: {cnt}")
        click.echo("")

    # 批量验证
    results = batch_verify(files, employee, strength)

    # 输出每个结果
    success_count = 0
    fail_count = 0
    for i, result in enumerate(results, 1):
        if not json_mode:
            click.echo(f"  [{i}/{len(results)}] ", nl=False)
        format_verify_result(result, json_mode=json_mode)
        if result.success and result.matched:
            success_count += 1
        else:
            fail_count += 1

    elapsed = time.monotonic() - start

    if not json_mode:
        format_batch_summary(
            total=len(results),
            success=success_count,
            failed=fail_count,
            skipped=0,
            elapsed=elapsed,
        )

    # 退出码：0=全成功, 1=部分失败, 2=全失败
    if fail_count == 0:
        raise SystemExit(0)
    elif success_count == 0:
        raise SystemExit(2)
    else:
        raise SystemExit(1)
