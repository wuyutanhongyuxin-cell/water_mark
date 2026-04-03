"""
水印策略路由模块。

根据 detector 的检测结果，从 watermark_rules.yaml 中匹配
对应的水印处理器，并实例化返回。

流程：detect_file_type() → category → 查 rules → 实例化处理器
"""

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional
import re

import yaml
from loguru import logger

from src.core.detector import DetectionResult, detect_file_type
from src.watermarks.base import WatermarkBase, WatermarkStrength


# 默认配置文件路径
_DEFAULT_RULES_PATH = Path(__file__).parent.parent.parent / "config" / "watermark_rules.yaml"
_DEFAULT_SETTINGS_PATH = Path(__file__).parent.parent.parent / "config" / "settings.yaml"


@dataclass
class RouteResult:
    """
    路由结果。

    Attributes:
        processor: 水印处理器实例（可能为 None）
        detection: 文件检测结果
        rule_params: 匹配到的规则参数
        error: 路由失败时的错误信息
    """
    processor: Optional[WatermarkBase]
    detection: DetectionResult
    rule_params: dict = field(default_factory=dict)
    error: str = ""


def load_rules(rules_path: Path = _DEFAULT_RULES_PATH) -> dict:
    """加载水印路由规则配置（带缓存）。Raises FileNotFoundError。"""
    return _load_rules_cached(str(rules_path))


def load_settings(settings_path: Path = _DEFAULT_SETTINGS_PATH) -> dict:
    """加载全局配置（带缓存）。"""
    return _load_settings_cached(str(settings_path))


@lru_cache(maxsize=4)
def _load_rules_cached(rules_path_str: str) -> dict:
    """内部缓存实现（lru_cache 要求参数可哈希，用 str）。"""
    rules_path = Path(rules_path_str)
    if not rules_path.exists():
        raise FileNotFoundError(f"Rules file not found: {rules_path}")
    try:
        with open(rules_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config.get("rules", {})
    except Exception as e:
        logger.error(f"Failed to load rules: {e}")
        raise


@lru_cache(maxsize=4)
def _load_settings_cached(settings_path_str: str) -> dict:
    """内部缓存实现。"""
    settings_path = Path(settings_path_str)
    if not settings_path.exists():
        return {}
    try:
        with open(settings_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning(f"Failed to load settings: {e}")
        return {}


# 白名单正则：只允许 "模块名.类名" 格式，防止路径遍历或任意模块注入
_PROCESSOR_PATH_RE = re.compile(r"^[a-zA-Z_]\w*\.[A-Za-z_]\w*$")


def _resolve_processor(processor_path: str, strength: WatermarkStrength) -> Optional[WatermarkBase]:
    """动态导入处理器。格式 "module_name.ClassName"，严格白名单校验。"""
    # 安全校验：必须是 "word.Word" 格式，禁止路径遍历和任意模块注入
    if not _PROCESSOR_PATH_RE.match(processor_path):
        logger.error(f"Invalid processor path (blocked): {processor_path}")
        return None
    try:
        module_name, class_name = processor_path.rsplit(".", 1)
        full_module = f"src.watermarks.{module_name}"
        import importlib
        module = importlib.import_module(full_module)
        cls = getattr(module, class_name)
        return cls(strength=strength)
    except (ImportError, AttributeError) as e:
        logger.warning(f"Processor not available: {processor_path} ({e})")
        return None
    except Exception as e:
        logger.error(f"Failed to resolve processor {processor_path}: {e}")
        return None


def route_file(
    file_path: Path,
    strength: WatermarkStrength = WatermarkStrength.MEDIUM,
    rules_path: Path = _DEFAULT_RULES_PATH,
) -> RouteResult:
    """
    对文件执行类型检测 + 策略路由。

    完整流程：
    1. detect_file_type() 检测文件类型
    2. 用 category 匹配 watermark_rules.yaml 中的规则
    3. 动态导入并实例化对应的水印处理器
    4. 返回 RouteResult（含处理器、检测结果、规则参数）

    Args:
        file_path: 待处理的文件路径
        strength: 水印嵌入强度
        rules_path: 规则配置文件路径

    Returns:
        RouteResult: 路由结果
    """
    # 1. 检测文件类型
    detection = detect_file_type(file_path)

    # 类型未识别
    if detection.category == "unknown":
        return RouteResult(
            processor=None, detection=detection,
            error=f"Unknown file type: {detection.mime_type}",
        )

    # 2. 加载规则并匹配
    try:
        rules = load_rules(rules_path)
    except Exception as e:
        return RouteResult(
            processor=None, detection=detection,
            error=f"Failed to load rules: {e}",
        )

    rule = rules.get(detection.category)
    if not rule:
        return RouteResult(
            processor=None, detection=detection,
            error=f"No rule defined for category: {detection.category}",
        )

    # 3. 实例化处理器
    processor_path = rule.get("processor", "")
    processor = _resolve_processor(processor_path, strength)

    if processor is None:
        # 处理器未实现（Phase 2+ 才会逐步添加），返回规则信息
        return RouteResult(
            processor=None, detection=detection,
            rule_params=rule.get("params", {}),
            error=f"Processor not yet implemented: {processor_path}",
        )

    return RouteResult(
        processor=processor, detection=detection,
        rule_params=rule.get("params", {}),
    )
