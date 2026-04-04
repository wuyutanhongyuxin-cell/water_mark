"""
统一水印嵌入接口。

对外暴露 embed_watermark() 单一入口，内部完成：
安全前置检查 → 策略路由 → 嵌入水印 → 自动验证 → 审计日志
"""

from pathlib import Path
from typing import Optional
import time

from loguru import logger

from src.core.router import route_file, load_settings
from src.security.audit import log_embed
from src.watermarks.base import (
    EmbedResult, WatermarkPayload, WatermarkStrength,
)


def _build_output_path(
    input_path: Path, output_dir: Optional[Path], naming_template: str,
) -> Path:
    """根据命名模板生成输出路径。output_dir 为 None 则与原文件同目录。"""
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
    """嵌入水印统一入口。始终返回 EmbedResult，不抛异常。"""
    start_time = time.monotonic()
    input_path = Path(input_path)

    # === 阶段0：安全前置检查（在路由之前完成） ===
    pre_err = _pre_checks(input_path, output_path, output_dir)
    if pre_err:
        log_embed(str(input_path), payload.employee_id, False, message=pre_err)
        return EmbedResult(
            success=False, message=pre_err,
            elapsed_time=time.monotonic() - start_time,
        )

    # 加载配置 + 生成输出路径
    settings = load_settings()
    if output_path is None:
        naming = settings.get("output", {}).get("naming", "{stem}_wm{ext}")
        default_dir = settings.get("output", {}).get("directory")
        if output_dir is None and default_dir:
            output_dir = Path(default_dir)
        output_path = _build_output_path(input_path, output_dir, naming)
    output_path = Path(output_path)

    # 输出路径安全检查
    path_err = _output_path_checks(input_path, output_path, settings)
    if path_err:
        log_embed(str(input_path), payload.employee_id, False, message=path_err)
        return EmbedResult(
            success=False, message=path_err,
            elapsed_time=time.monotonic() - start_time,
        )

    # === 阶段1：路由匹配 ===
    try:
        route = route_file(input_path, strength=strength)
    except Exception as e:
        log_embed(str(input_path), payload.employee_id, False, message=f"Routing error: {e}")
        return EmbedResult(
            success=False, message=f"Routing error: {e}",
            elapsed_time=time.monotonic() - start_time,
        )
    if route.processor is None:
        log_embed(str(input_path), payload.employee_id, False, message=f"Routing failed: {route.error}")
        return EmbedResult(
            success=False, message=f"Routing failed: {route.error}",
            elapsed_time=time.monotonic() - start_time,
        )

    # 文件预检查（处理器级别）
    if not route.processor.validate_file(input_path):
        log_embed(str(input_path), payload.employee_id, False, message="File validation failed")
        return EmbedResult(
            success=False, message=f"File validation failed: {input_path}",
            elapsed_time=time.monotonic() - start_time,
        )

    # === 阶段2：执行嵌入 ===
    try:
        result = route.processor.embed(input_path, payload, output_path)
    except Exception as e:
        logger.exception(f"Embed failed for {input_path}: {e}")
        _rollback(output_path)
        log_embed(str(input_path), payload.employee_id, False, message=str(e))
        return EmbedResult(
            success=False, message=f"Embed error: {e}",
            elapsed_time=time.monotonic() - start_time,
        )

    if not result.success:
        _rollback(output_path)
        result.elapsed_time = time.monotonic() - start_time
        result.output_path = None
        log_embed(str(input_path), payload.employee_id, False, message=result.message)
        return result

    # === 阶段3：自动验证（fail-closed） ===
    if auto_verify:
        verify_err = _auto_verify(route.processor, output_path, payload)
        if verify_err:
            _rollback(output_path)
            log_embed(str(input_path), payload.employee_id, False, message=verify_err)
            return EmbedResult(
                success=False, output_path=None, message=verify_err,
                elapsed_time=time.monotonic() - start_time,
            )

    result.elapsed_time = time.monotonic() - start_time
    log_embed(
        str(input_path), payload.employee_id, True,
        output_path=str(output_path), message=result.message,
    )
    logger.info(
        f"Embedded watermark: {input_path.name} -> {output_path.name} "
        f"({result.elapsed_time:.2f}s)"
    )
    return result


def _pre_checks(
    input_path: Path, output_path: Optional[Path], output_dir: Optional[Path],
) -> Optional[str]:
    """输入文件前置检查，返回错误信息或 None。"""
    if not input_path.exists():
        return f"Input file not found: {input_path}"
    if not input_path.is_file():
        return f"Input path is not a file: {input_path}"
    # 文件大小限制
    settings = load_settings()
    max_mb = settings.get("watermark", {}).get("max_file_size_mb", 500)
    file_size_mb = input_path.stat().st_size / (1024 * 1024)
    if file_size_mb > max_mb:
        return f"File too large: {file_size_mb:.1f}MB > {max_mb}MB limit"
    return None


def _output_path_checks(
    input_path: Path, output_path: Path, settings: dict,
) -> Optional[str]:
    """输出路径安全检查，返回错误信息或 None。"""
    # 禁止输出 == 输入（回滚会删原文件）
    if output_path.resolve() == input_path.resolve():
        return "Output path must differ from input path (rollback safety)"
    # overwrite 策略
    overwrite = settings.get("output", {}).get("overwrite", False)
    if not overwrite and output_path.exists():
        return f"Output file exists and overwrite=false: {output_path}"
    return None


def _auto_verify(processor, output_path: Path, payload) -> Optional[str]:
    """自动验证（fail-closed），返回错误信息或 None。"""
    try:
        verified = processor.verify(output_path, payload)
        if not verified:
            logger.error(f"Post-embed verification FAILED: {output_path}")
            return "Verification failed after embedding"
        logger.info(f"Verification passed: {output_path}")
        return None
    except Exception as e:
        logger.exception(f"Verification exception (fail-closed): {e}")
        return f"Verification error: {e}"


def _rollback(output_path: Path) -> None:
    """删除不完整的输出文件（嵌入失败时的回滚操作）。"""
    try:
        if output_path.exists():
            output_path.unlink()
            logger.info(f"Rolled back incomplete file: {output_path}")
    except Exception as e:
        logger.warning(f"Rollback failed: {e}")
