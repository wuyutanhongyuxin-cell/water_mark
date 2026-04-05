"""
临时文件清理服务。

提供过期文件清理功能，被 TaskManager 调用。
支持独立运行和守护线程模式。
"""

import datetime
import time

from loguru import logger


def cleanup_old_files(max_age_minutes: int = 30) -> int:
    """
    清理过期临时文件（上传目录和输出目录）。

    Args:
        max_age_minutes: 文件最大保留时间（分钟），0 表示清理全部

    Returns:
        清理的文件数量
    """
    # 延迟导入避免循环依赖
    from src.web.dependencies import UPLOAD_DIR, OUTPUT_DIR

    now = datetime.datetime.now().timestamp()
    cleaned = 0

    for directory in (UPLOAD_DIR, OUTPUT_DIR):
        if not directory.exists():
            continue
        for f in directory.iterdir():
            if not f.is_file():
                continue
            try:
                age_min = (now - f.stat().st_mtime) / 60
                if age_min > max_age_minutes:
                    f.unlink()
                    cleaned += 1
            except OSError as e:
                logger.warning(f"清理文件失败: {f} - {e}")

    if cleaned > 0:
        logger.info(f"已清理 {cleaned} 个过期临时文件")
    return cleaned


def run_cleanup_daemon() -> None:
    """
    后台守护线程入口：每 10 分钟清理一次过期文件。

    此函数为阻塞式无限循环，应在 daemon=True 线程中运行。
    """
    while True:
        time.sleep(600)  # 10 分钟
        try:
            cleanup_old_files()
        except Exception as e:
            logger.error(f"清理守护线程异常: {e}")
