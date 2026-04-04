"""
目录扫描模块。

从 watermark_rules.yaml 动态读取支持的扩展名，
扫描目录并过滤出可处理文件（跳过隐藏文件和超大文件）。
"""

from collections import Counter
from pathlib import Path

from loguru import logger

from src.core.router import load_rules, load_settings


def _build_ext_map() -> dict:
    """
    构建 扩展名→类别 的反向映射（一次构建，多处复用）。

    Returns:
        dict[str, str]: {".jpg": "image", ".pdf": "pdf", ...}
    """
    rules = load_rules()
    ext_map = {}
    for category, rule in rules.items():
        if category == "unknown":
            continue
        for ext in rule.get("extensions", []):
            ext_map[ext.lower()] = category
    return ext_map


def get_supported_extensions() -> set:
    """
    从 watermark_rules.yaml 动态读取所有支持的文件扩展名。

    Returns:
        set[str]: 扩展名集合，如 {".jpg", ".png", ".pdf", ...}
    """
    return set(_build_ext_map().keys())


def _is_hidden(path: Path) -> bool:
    """检查文件或任一父目录是否以 . 开头（隐藏文件/目录）。"""
    for part in path.parts:
        if part.startswith("."):
            return True
    return False


def scan_directory(
    dir_path: Path,
    recursive: bool = True,
    max_size_mb: float = 0,
) -> list:
    """
    扫描目录，返回可处理文件列表。

    过滤规则：
    1. 跳过隐藏文件和隐藏目录
    2. 只保留受支持的扩展名
    3. 跳过超大文件（max_size_mb > 0 时）

    Args:
        dir_path: 待扫描目录
        recursive: 是否递归扫描子目录
        max_size_mb: 最大文件大小 (MB)，0 表示使用配置默认值

    Returns:
        list[Path]: 可处理文件的路径列表（按名称排序）
    """
    dir_path = Path(dir_path)
    if not dir_path.is_dir():
        logger.error(f"Not a directory: {dir_path}")
        return []

    # 从配置读取大小限制
    if max_size_mb <= 0:
        settings = load_settings()
        max_size_mb = settings.get("watermark", {}).get("max_file_size_mb", 500)

    supported = get_supported_extensions()
    pattern = "**/*" if recursive else "*"
    files = []

    for p in dir_path.glob(pattern):
        # 跳过目录
        if not p.is_file():
            continue
        # 跳过隐藏文件/目录
        # 用相对路径检查，避免绝对路径中的误判
        try:
            rel = p.relative_to(dir_path)
        except ValueError:
            continue
        if _is_hidden(rel):
            continue
        # 扩展名过滤
        if p.suffix.lower() not in supported:
            continue
        # 大小过滤
        try:
            size_mb = p.stat().st_size / (1024 * 1024)
            if size_mb > max_size_mb:
                logger.info(f"Skipped (too large): {p.name} ({size_mb:.1f}MB)")
                continue
        except OSError:
            continue
        files.append(p)

    # 按文件名排序，确保输出顺序一致
    files.sort(key=lambda f: f.name.lower())
    return files


def scan_summary(files: list) -> dict:
    """
    按文件类别统计扫描结果。

    Args:
        files: scan_directory 返回的文件列表

    Returns:
        dict: {"image": 5, "pdf": 3, "text": 2, ...}
    """
    ext_map = _build_ext_map()
    counter = Counter()
    for f in files:
        category = ext_map.get(f.suffix.lower(), "unknown")
        counter[category] += 1
    return dict(counter)
