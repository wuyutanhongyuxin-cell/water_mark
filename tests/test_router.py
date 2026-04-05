"""
水印策略路由模块测试。

测试 src.core.router 的规则加载和路由分发：
- load_rules() 从 YAML 加载规则，带 lru_cache
- load_settings() 从 YAML 加载设置，缺失时返回 {}
- route_file() 检测文件 → 匹配规则 → 实例化处理器
"""

from pathlib import Path

import pytest

from src.core.router import RouteResult, load_rules, load_settings, route_file
from src.watermarks.image_wm import ImageWatermark
from src.watermarks.text_wm import TextWatermark
from src.watermarks.pdf_wm import PdfWatermark
from src.watermarks.office_wm import OfficeWatermark


# 实际配置文件路径
_RULES_PATH = Path(__file__).parent.parent / "config" / "watermark_rules.yaml"
_SETTINGS_PATH = Path(__file__).parent.parent / "config" / "settings.yaml"


# ========== load_rules 测试 ==========

class TestLoadRules:
    """规则配置加载。"""

    def test_load_rules_returns_dict(self):
        """正常加载：返回包含各类别键的 dict。"""
        rules = load_rules(_RULES_PATH)
        assert isinstance(rules, dict)
        # 至少包含核心类别
        for cat in ("image", "pdf", "text", "office_word", "audio", "video"):
            assert cat in rules, f"Missing category: {cat}"

    def test_load_rules_file_not_found(self, tmp_path):
        """规则文件不存在 → FileNotFoundError。"""
        missing = tmp_path / "missing_rules.yaml"
        with pytest.raises(FileNotFoundError):
            load_rules(missing)

    def test_load_rules_has_processor_field(self):
        """每条规则应包含 processor 字段。"""
        rules = load_rules(_RULES_PATH)
        for cat in ("image", "pdf", "text"):
            assert "processor" in rules[cat], (
                f"Category '{cat}' missing 'processor' field"
            )


# ========== load_settings 测试 ==========

class TestLoadSettings:
    """全局设置加载。"""

    def test_load_settings_returns_dict(self):
        """正常加载：返回 dict。"""
        settings = load_settings(_SETTINGS_PATH)
        assert isinstance(settings, dict)

    def test_load_settings_missing_file_returns_empty(self, tmp_path):
        """设置文件不存在 → 返回空 dict（不报错）。"""
        missing = tmp_path / "missing_settings.yaml"
        result = load_settings(missing)
        assert result == {}


# ========== route_file 路由测试 ==========

class TestRouteFile:
    """文件路由分发：检测 + 匹配规则 + 实例化处理器。"""

    def test_route_png_image(self, sample_image):
        """PNG 图像 → ImageWatermark 处理器。"""
        result = route_file(sample_image)
        assert isinstance(result, RouteResult)
        assert isinstance(result.processor, ImageWatermark)
        assert result.detection.category == "image"
        assert result.error == ""

    def test_route_txt_file(self, sample_txt):
        """TXT 文件 → TextWatermark 处理器。"""
        result = route_file(sample_txt)
        assert isinstance(result.processor, TextWatermark)
        assert result.detection.category == "text"

    def test_route_pdf_file(self, sample_pdf):
        """PDF 文件 → PdfWatermark 处理器。"""
        result = route_file(sample_pdf)
        assert isinstance(result.processor, PdfWatermark)
        assert result.detection.category == "pdf"

    def test_route_docx_file(self, sample_docx):
        """DOCX 文件 → OfficeWatermark 处理器。"""
        result = route_file(sample_docx)
        assert isinstance(result.processor, OfficeWatermark)
        assert result.detection.category == "office_word"

    def test_route_unknown_file(self, tmp_path):
        """未知文件类型 → processor=None, error 包含 'Unknown'。"""
        unknown = tmp_path / "data.xyz"
        unknown.write_bytes(b"\xfe\xed\xfa\xce" * 100)
        result = route_file(unknown)
        assert result.processor is None
        assert "Unknown" in result.error

    def test_route_returns_rule_params(self, sample_image):
        """路由结果应包含规则参数（如 block_size, wavelet 等）。"""
        result = route_file(sample_image)
        assert isinstance(result.rule_params, dict)
        # image 规则应有 block_size 参数
        assert "block_size" in result.rule_params

    def test_route_detection_info(self, sample_pdf):
        """RouteResult.detection 应包含完整的检测信息。"""
        result = route_file(sample_pdf)
        assert result.detection.mime_type == "application/pdf"
        assert result.detection.extension == ".pdf"
        assert result.detection.confidence > 0
