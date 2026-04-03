"""
统一水印嵌入接口。

对外暴露 embed_watermark() 单一入口，内部完成：
文件检测 → 策略路由 → 嵌入水印 → 自动验证 → 审计日志
"""

from pathlib import Path
from typing import Optional
import logging
import time

from src.core.router import route_file, load_settings
from src.watermarks.base import (
    EmbedResult, WatermarkPayload, WatermarkStrength,
)

logger = logging.getLogger(__name__)


def _build_output_path(
    input_path: Path,
    output_dir: Optional[Path],
    naming_template: str,
) -> Path:
    """
    根据命名模板生成输出文件路径。

    Args:
        input_path: 原始文件路径
        output_dir: 输出目录（None 则与原文件同目录）
        naming_template: 命名模板，如 "{stem}_wm{ext}"

    Returns:
        输出文件的 Path 对象
    """
    stem = input_path.stem
    ext = input_path.suffix
    filename = naming_template.format(stem=stem, ext=ext)
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir / filename
    return input_path.parent / filename


def embed_watermark(
    input_path: Path,
    payload: WatermarkPayload,
    output_path: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    strength: WatermarkStrength = WatermarkStrength.MEDIUM,
    auto_verify: bool = True,
) -> EmbedResult:
    """
    嵌入水印的统一入口。

    完整流程：
    1. 路由：检测文件类型 → 匹配水印处理器
    2. 嵌入：调用处理器的 embed() 方法
    3. 验证：嵌入后立即提取验证（auto_verify=True 时）
    4. 失败时回滚（删除不完整的输出文件）

    Args:
        input_path: 原始文件路径
        payload: 水印载荷（员工ID、时间戳等）
        output_path: 指定输出路径（优先级高于 output_dir）
        output_dir: 输出目录（使用命名模板生成文件名）
        strength: 水印嵌入强度
        auto_verify: 是否自动验证

    Returns:
        EmbedResult: 嵌入结果
    """
    start_time = time.time()
    input_path = Path(input_path)

    # 1. 路由匹配
    route = route_file(input_path, strength=strength)
    if route.processor is None:
        return EmbedResult(
            success=False,
            message=f"Routing failed: {route.error}",
            elapsed_time=time.time() - start_time,
        )

    # 2. 生成输出路径
    if output_path is None:
        settings = load_settings()
        naming = settings.get("output", {}).get("naming", "{stem}_wm{ext}")
        default_dir = settings.get("output", {}).get("directory")
        if output_dir is None and default_dir:
            output_dir = Path(default_dir)
        output_path = _build_output_path(input_path, output_dir, naming)
    output_path = Path(output_path)

    # 3. 文件预检查
    if not route.processor.validate_file(input_path):
        return EmbedResult(
            success=False,
            message=f"File validation failed: {input_path}",
            elapsed_time=time.time() - start_time,
        )

    # 4. 执行嵌入
    try:
        result = route.processor.embed(input_path, payload, output_path)
    except Exception as e:
        logger.error(f"Embed failed for {input_path}: {e}")
        _rollback(output_path)
        return EmbedResult(
            success=False,
            message=f"Embed error: {e}",
            elapsed_time=time.time() - start_time,
        )

    # 嵌入失败，回滚
    if not result.success:
        _rollback(output_path)
        result.elapsed_time = time.time() - start_time
        return result

    # 5. 自动验证
    if auto_verify and result.success:
        try:
            verified = route.processor.verify(output_path, payload)
            if not verified:
                logger.error(f"Post-embed verification FAILED: {output_path}")
                _rollback(output_path)
                return EmbedResult(
                    success=False, output_path=output_path,
                    message="Verification failed after embedding",
                    elapsed_time=time.time() - start_time,
                )
            logger.info(f"Verification passed: {output_path}")
        except Exception as e:
            logger.warning(f"Verification error (non-fatal): {e}")

    result.elapsed_time = time.time() - start_time
    logger.info(
        f"Embedded watermark: {input_path.name} -> {output_path.name} "
        f"({result.elapsed_time:.2f}s)"
    )
    return result


def _rollback(output_path: Path) -> None:
    """删除不完整的输出文件（嵌入失败时的回滚操作）。"""
    try:
        if output_path.exists():
            output_path.unlink()
            logger.info(f"Rolled back incomplete file: {output_path}")
    except Exception as e:
        logger.warning(f"Rollback failed: {e}")
