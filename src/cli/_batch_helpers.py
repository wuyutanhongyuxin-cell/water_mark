"""
batch 命令辅助函数。

从 batch_cmd.py 拆分出来的共享工具：
文件嵌入、AI 建议、用户选择解析、dry-run 显示等。
"""

from pathlib import Path

import click

from src.cli import info, warn, format_embed_result
from src.watermarks.base import WatermarkPayload


def embed_one(file_path, employee, strength, out_dir, no_verify):
    """嵌入单个文件（所有模式共用）。"""
    from src.core.embedder import embed_watermark

    payload = WatermarkPayload(employee_id=employee)
    return embed_watermark(
        input_path=file_path,
        payload=payload,
        output_dir=out_dir,
        strength=strength,
        auto_verify=not no_verify,
    )


def check_ai_available() -> bool:
    """检查 AI 功能是否可用。"""
    try:
        from src.ai import is_ai_enabled
        return is_ai_enabled()
    except Exception:
        return False


def show_ai_suggestion(file_path: Path) -> None:
    """显示 AI 敏感度分析建议。"""
    try:
        from src.ai import analyze_sensitivity
        result = analyze_sensitivity(file_path)
        if result.from_ai:
            info(f"AI suggestion: {result.recommended_strength} "
                 f"(sensitivity {result.sensitivity_level}/5)")
            if result.reasoning:
                info(f"Reason: {result.reasoning}")
    except Exception:
        pass  # AI 失败不影响流程


def show_dry_run(files: list) -> None:
    """列出文件清单，不执行任何操作。"""
    click.echo(click.style("\n  [DRY RUN] Files to process:", fg="cyan"))
    for i, f in enumerate(files, 1):
        size_mb = f.stat().st_size / (1024 * 1024)
        click.echo(f"  {i:3d}. {f.name} ({size_mb:.1f}MB)")
    click.echo(f"\n  Total: {len(files)} files")


def parse_selection(text: str, total: int) -> list:
    """
    解析用户选择字符串。

    支持格式：
      "all" → 全选
      "1-5,8,10" → 选择 1-5, 8, 10
      "3" → 选择 3

    Returns:
        list[int]: 选中的文件索引（0-based）
    """
    text = text.strip().lower()
    if text == "all":
        return list(range(total))

    indices = set()
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            try:
                start_str, end_str = part.split("-", 1)
                start = int(start_str.strip())
                end = int(end_str.strip())
                for n in range(start, end + 1):
                    if 1 <= n <= total:
                        indices.add(n - 1)
            except ValueError:
                continue
        else:
            try:
                n = int(part)
                if 1 <= n <= total:
                    indices.add(n - 1)
            except ValueError:
                continue

    return sorted(indices)


def exit_code(success: int, failed: int) -> int:
    """根据处理结果返回退出码。0=全成功, 1=部分失败, 2=全失败。"""
    if failed == 0:
        return 0
    if success == 0:
        return 2
    return 1
