"""
batch 命令 — 批量水印嵌入。

支持三种模式：
  auto:   全自动，零交互
  semi:   半自动，逐文件确认 + AI 建议
  manual: 手动选择要处理的文件
"""

import time
from pathlib import Path

import click

from src.cli import (
    fail, info, warn,
    resolve_strength,
    format_embed_result,
    format_batch_summary,
)
from src.cli.scan import scan_directory, scan_summary
from src.cli._batch_helpers import (
    embed_one, check_ai_available, show_ai_suggestion,
    show_dry_run, parse_selection, exit_code,
)
from src.watermarks.base import WatermarkStrength
from src.core.router import load_settings
_STRENGTH_CHOICES = [s.value for s in WatermarkStrength]


@click.command()
@click.option("-d", "--dir", "dir_path", required=True,
              type=click.Path(exists=True, file_okay=False),
              help="Directory to process")
@click.option("-e", "--employee", required=True, help="Employee ID")
@click.option("-o", "--output-dir", default=None,
              type=click.Path(), help="Output directory")
@click.option("-s", "--strength", default=None,
              type=click.Choice(_STRENGTH_CHOICES),
              help="Watermark strength (default: from config)")
@click.option("-m", "--mode", default="auto",
              type=click.Choice(["auto", "semi", "manual"]),
              help="Processing mode (default: auto)")
@click.option("--recursive/--no-recursive", default=None,
              help="Recursive scan (default: from config)")
@click.option("--skip-errors/--no-skip-errors", default=None,
              help="Skip errors (default: from config)")
@click.option("--dry-run", is_flag=True, default=False,
              help="List files only, do not process")
@click.option("--no-verify", is_flag=True, default=False,
              help="Skip post-embed verification")
def batch(dir_path, employee, output_dir, strength, mode,
          recursive, skip_errors, dry_run, no_verify):
    """Batch embed watermarks into directory."""
    settings = load_settings()
    batch_cfg = settings.get("batch", {})

    # 解析配置参数
    wm_strength = resolve_strength(strength)
    if recursive is None:
        recursive = batch_cfg.get("recursive", True)
    if skip_errors is None:
        skip_errors = batch_cfg.get("skip_errors", False)

    out_dir = Path(output_dir) if output_dir else None
    target = Path(dir_path)

    # 扫描目录
    files = scan_directory(target, recursive=recursive)
    if not files:
        warn("No supported files found")
        raise SystemExit(0)

    # 显示扫描结果
    summary = scan_summary(files)
    click.echo(f"\n  Scanned: {len(files)} files in {target}")
    for cat, cnt in sorted(summary.items()):
        info(f"{cat}: {cnt}")

    # dry-run 模式：仅列出文件
    if dry_run:
        show_dry_run(files)
        raise SystemExit(0)

    # 根据模式分发
    if mode == "auto":
        code = _run_auto(files, employee, wm_strength, out_dir,
                         no_verify, skip_errors)
    elif mode == "semi":
        code = _run_semi(files, employee, wm_strength, out_dir,
                         no_verify, skip_errors)
    else:
        code = _run_manual(files, employee, wm_strength, out_dir,
                           no_verify, skip_errors)
    raise SystemExit(code)


def _run_auto(files, employee, strength, out_dir, no_verify, skip_errors):
    """全自动模式：顺序处理全部文件。"""
    click.echo(click.style("\n  [AUTO] Processing all files...", fg="cyan"))
    start = time.monotonic()
    success, failed, skipped = 0, 0, 0

    for i, f in enumerate(files, 1):
        click.echo(f"\n  [{i}/{len(files)}] {f.name}")
        result = embed_one(f, employee, strength, out_dir, no_verify)
        format_embed_result(result, f.name)
        if result.success:
            success += 1
        else:
            failed += 1
            if not skip_errors:
                fail("Stopping on error (use --skip-errors to continue)")
                break

    elapsed = time.monotonic() - start
    format_batch_summary(len(files), success, failed, skipped, elapsed)
    return exit_code(success, failed)


def _run_semi(files, employee, strength, out_dir, no_verify, skip_errors):
    """半自动模式：逐文件显示信息，等待用户确认。"""
    click.echo(click.style("\n  [SEMI] Review each file...", fg="cyan"))
    start = time.monotonic()
    success, failed, skipped = 0, 0, 0
    ai_available = check_ai_available()

    for i, f in enumerate(files, 1):
        size_mb = f.stat().st_size / (1024 * 1024)
        click.echo(f"\n  [{i}/{len(files)}] {f.name} ({f.suffix}, {size_mb:.1f}MB)")

        if ai_available:
            show_ai_suggestion(f)

        choice = click.prompt(
            "    Process?",
            type=click.Choice(["y", "n", "s", "q"], case_sensitive=False),
            default="y", show_choices=True,
        )

        if choice.lower() == "q":
            warn("User quit")
            break
        if choice.lower() in ("n", "s"):
            info("Skipped")
            skipped += 1
            continue

        result = embed_one(f, employee, strength, out_dir, no_verify)
        format_embed_result(result, f.name)
        if result.success:
            success += 1
        else:
            failed += 1
            if not skip_errors:
                fail("Stopping on error")
                break

    elapsed = time.monotonic() - start
    format_batch_summary(len(files), success, failed, skipped, elapsed)
    return exit_code(success, failed)


def _run_manual(files, employee, strength, out_dir, no_verify, skip_errors):
    """手动模式：显示编号列表，用户选择要处理的文件。"""
    click.echo(click.style("\n  [MANUAL] Select files:", fg="cyan"))
    for i, f in enumerate(files, 1):
        size_mb = f.stat().st_size / (1024 * 1024)
        click.echo(f"  {i:3d}. {f.name} ({size_mb:.1f}MB)")

    selection_str = click.prompt(
        "\n  Enter selection (e.g., 1-5,8,10 or 'all')",
        type=str, default="all",
    )
    selected = parse_selection(selection_str, len(files))
    if not selected:
        warn("No files selected")
        return 0

    selected_files = [files[i] for i in selected]
    click.echo(f"\n  Selected {len(selected_files)} files")

    start = time.monotonic()
    success, failed, skipped = 0, 0, 0

    for i, f in enumerate(selected_files, 1):
        click.echo(f"\n  [{i}/{len(selected_files)}] {f.name}")
        result = embed_one(f, employee, strength, out_dir, no_verify)
        format_embed_result(result, f.name)
        if result.success:
            success += 1
        else:
            failed += 1
            if not skip_errors:
                fail("Stopping on error")
                break

    elapsed = time.monotonic() - start
    format_batch_summary(len(selected_files), success, failed, skipped, elapsed)
    return exit_code(success, failed)
