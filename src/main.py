"""
WatermarkForge CLI 主入口。

Click group + embed / extract 命令。
verify / batch 命令从 cli 子模块导入注册。

用法：
    python -m src.main <command> [options]
"""

from pathlib import Path
from typing import Optional

import click

from src.cli import (
    ok, fail, info, warn,
    resolve_strength,
    parse_custom_data,
    format_embed_result,
    format_extract_result,
)
from src.watermarks.base import WatermarkPayload, WatermarkStrength

# 从枚举动态生成 Click 选项，避免硬编码字符串
_STRENGTH_CHOICES = [s.value for s in WatermarkStrength]


# ========== Click Group ==========

@click.group()
@click.version_option(version="0.7.0", prog_name="WatermarkForge")
def cli():
    """WatermarkForge — 企业文档盲水印自动化系统。"""
    pass


# ========== embed 命令 ==========

@cli.command()
@click.option("-i", "--input", "input_path", required=True,
              type=click.Path(exists=True, dir_okay=False),
              help="Input file path")
@click.option("-e", "--employee", required=True, help="Employee ID (e.g., E001)")
@click.option("-o", "--output", "output_path", default=None,
              type=click.Path(), help="Output file path")
@click.option("-d", "--output-dir", default=None,
              type=click.Path(), help="Output directory")
@click.option("-s", "--strength", default=None,
              type=click.Choice(_STRENGTH_CHOICES),
              help="Watermark strength (default: from config)")
@click.option("--no-verify", is_flag=True, default=False,
              help="Skip post-embed verification")
@click.option("-c", "--custom", multiple=True,
              help="Custom metadata key=value (repeatable)")
def embed(input_path, employee, output_path, output_dir, strength, no_verify, custom):
    """Embed watermark into a file."""
    from src.core.embedder import embed_watermark

    # 解析参数
    wm_strength = resolve_strength(strength)
    custom_data = parse_custom_data(custom)
    in_path = Path(input_path)
    out_path = Path(output_path) if output_path else None
    out_dir = Path(output_dir) if output_dir else None

    click.echo(f"\n  Embedding watermark into: {in_path.name}")
    info(f"Employee: {employee}, Strength: {wm_strength.value}")

    # 构建载荷
    payload = WatermarkPayload(
        employee_id=employee,
        custom_data=custom_data,
    )

    # 执行嵌入
    result = embed_watermark(
        input_path=in_path,
        payload=payload,
        output_path=out_path,
        output_dir=out_dir,
        strength=wm_strength,
        auto_verify=not no_verify,
    )

    format_embed_result(result, in_path.name)

    # 退出码
    raise SystemExit(0 if result.success else 2)


# ========== extract 命令 ==========

@cli.command()
@click.option("-i", "--input", "input_path", required=True,
              type=click.Path(exists=True, dir_okay=False),
              help="Watermarked file path")
@click.option("-s", "--strength", default=None,
              type=click.Choice(_STRENGTH_CHOICES),
              help="Watermark strength (default: from config)")
@click.option("--json", "json_mode", is_flag=True, default=False,
              help="Output in JSON format")
def extract(input_path, strength, json_mode):
    """Extract watermark from a file."""
    from src.core.extractor import extract_watermark

    wm_strength = resolve_strength(strength)
    in_path = Path(input_path)

    if not json_mode:
        click.echo(f"\n  Extracting watermark from: {in_path.name}")

    result = extract_watermark(file_path=in_path, strength=wm_strength)
    format_extract_result(result, in_path.name, json_mode)

    raise SystemExit(0 if result.success else 2)


# ========== 注册子命令 ==========

def _register_subcommands():
    """延迟导入并注册 verify / batch 子命令。"""
    from src.cli.verify_cmd import verify
    from src.cli.batch_cmd import batch
    cli.add_command(verify)
    cli.add_command(batch)


_register_subcommands()


# ========== 入口点 ==========

if __name__ == "__main__":
    cli()
