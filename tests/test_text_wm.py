"""
纯文本零宽字符水印处理器测试。

测试 TextWatermark 对 TXT/CSV/JSON/MD 的嵌入/提取往返、
短文本拒绝、输出编码、支持格式列表。
"""

import json

import pytest

from src.watermarks.base import WatermarkStrength
from src.watermarks.text_wm import TextWatermark


# ========== 辅助函数 ==========


def _make_processor():
    """创建文本水印处理器（强度对零宽字符无影响，使用默认即可）。"""
    return TextWatermark(strength=WatermarkStrength.MEDIUM)


# ========== 各格式往返测试 ==========


class TestTextRoundtrip:
    """嵌入后提取，验证水印载荷一致性。"""

    def test_txt_roundtrip(self, sample_txt, sample_payload, tmp_path):
        """TXT 文件嵌入→提取，employee_id 应一致。"""
        wm = _make_processor()
        output = tmp_path / "output.txt"

        embed_result = wm.embed(sample_txt, sample_payload, output)
        assert embed_result.success, f"Embed failed: {embed_result.message}"

        extract_result = wm.extract(output)
        assert extract_result.success, f"Extract failed: {extract_result.message}"
        assert extract_result.payload is not None
        assert extract_result.payload.employee_id == "E001"

    def test_csv_roundtrip(self, sample_csv, sample_payload, tmp_path):
        """CSV 文件嵌入→提取，employee_id 应一致。"""
        wm = _make_processor()
        output = tmp_path / "output.csv"

        embed_result = wm.embed(sample_csv, sample_payload, output)
        assert embed_result.success, f"Embed failed: {embed_result.message}"

        extract_result = wm.extract(output)
        assert extract_result.success, f"Extract failed: {extract_result.message}"
        assert extract_result.payload is not None
        assert extract_result.payload.employee_id == "E001"

    def test_json_roundtrip_and_parseable(self, sample_json, sample_payload, tmp_path):
        """
        JSON 文件嵌入→提取，employee_id 一致。
        嵌入后去除零宽字符仍可解析为合法 JSON。
        """
        wm = _make_processor()
        output = tmp_path / "output.json"

        embed_result = wm.embed(sample_json, sample_payload, output)
        assert embed_result.success, f"Embed failed: {embed_result.message}"

        # 提取水印
        extract_result = wm.extract(output)
        assert extract_result.success, f"Extract failed: {extract_result.message}"
        assert extract_result.payload is not None
        assert extract_result.payload.employee_id == "E001"

        # 去除零宽字符后仍可解析为 JSON
        content = output.read_text(encoding="utf-8")
        # 零宽字符 Unicode 范围：U+200B ~ U+200F, U+FEFF 等
        zwc_chars = set("\u200b\u200c\u200d\u200e\u200f\u2060\ufeff")
        cleaned = "".join(ch for ch in content if ch not in zwc_chars)
        parsed = json.loads(cleaned)
        assert isinstance(parsed, dict)

    def test_md_roundtrip(self, sample_md, sample_payload, tmp_path):
        """Markdown 文件嵌入→提取，employee_id 应一致。"""
        wm = _make_processor()
        output = tmp_path / "output.md"

        embed_result = wm.embed(sample_md, sample_payload, output)
        assert embed_result.success, f"Embed failed: {embed_result.message}"

        extract_result = wm.extract(output)
        assert extract_result.success, f"Extract failed: {extract_result.message}"
        assert extract_result.payload is not None
        assert extract_result.payload.employee_id == "E001"


# ========== 短文本拒绝测试 ==========


class TestShortText:
    """文本过短时应拒绝嵌入。"""

    def test_text_too_short_fails(self, sample_payload, tmp_path):
        """少于 10 个字符的文本，embed 应失败并返回提示信息。"""
        wm = _make_processor()
        short_file = tmp_path / "short.txt"
        short_file.write_text("Hi", encoding="utf-8")
        output = tmp_path / "output.txt"

        result = wm.embed(short_file, sample_payload, output)
        assert not result.success
        # 错误信息应包含相关提示
        assert "short" in result.message.lower() or "min" in result.message.lower()


# ========== 输出编码测试 ==========


class TestOutputEncoding:
    """嵌入后的文件应为合法 UTF-8。"""

    def test_output_is_utf8(self, sample_txt, sample_payload, tmp_path):
        """输出文件可用 UTF-8 正常读取，不抛异常。"""
        wm = _make_processor()
        output = tmp_path / "output.txt"
        wm.embed(sample_txt, sample_payload, output)

        # 不应抛出 UnicodeDecodeError
        content = output.read_text(encoding="utf-8")
        assert len(content) > 0


# ========== 支持扩展名测试 ==========


class TestSupportedExtensions:
    """验证 supported_extensions 返回正确的格式列表。"""

    def test_supported_extensions(self):
        """应包含 .txt / .csv / .json / .md 四种格式。"""
        wm = _make_processor()
        exts = wm.supported_extensions()
        assert exts == [".txt", ".csv", ".json", ".md"]
