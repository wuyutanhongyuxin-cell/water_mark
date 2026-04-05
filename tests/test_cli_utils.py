"""
CLI 工具函数测试。

测试 src.cli 模块（__init__.py）的共享工具：
- resolve_strength: 强度字符串 → 枚举
- parse_custom_data: key=value 元组 → 字典
- format_embed_result / format_extract_result / format_verify_result: 结果格式化
"""

from pathlib import Path
import json

import pytest
import click

from src.cli import (
    resolve_strength,
    parse_custom_data,
    format_embed_result,
    format_extract_result,
    format_verify_result,
)
from src.watermarks.base import (
    EmbedResult, ExtractResult, WatermarkPayload, WatermarkStrength,
)
from src.core.verifier import VerifyResult


# ========== resolve_strength ==========

class TestResolveStrength:
    """测试强度解析。"""

    def test_low(self):
        """'low' → WatermarkStrength.LOW"""
        assert resolve_strength("low") == WatermarkStrength.LOW

    def test_medium(self):
        """'medium' → WatermarkStrength.MEDIUM"""
        assert resolve_strength("medium") == WatermarkStrength.MEDIUM

    def test_high(self):
        """'high' → WatermarkStrength.HIGH"""
        assert resolve_strength("high") == WatermarkStrength.HIGH

    def test_none_uses_config_default(self):
        """None → 从 settings.yaml 读取默认值（'medium'）。"""
        result = resolve_strength(None)
        # settings.yaml 中 default_strength 为 "medium"
        assert result == WatermarkStrength.MEDIUM

    def test_invalid_raises(self):
        """无效字符串 → ValueError。"""
        with pytest.raises(ValueError):
            resolve_strength("ultra")


# ========== parse_custom_data ==========

class TestParseCustomData:
    """测试自定义元数据解析。"""

    def test_normal(self):
        """正常 key=value 对。"""
        result = parse_custom_data(("dept=Finance", "level=3"))
        assert result == {"dept": "Finance", "level": "3"}

    def test_no_equals(self):
        """缺少 '=' 的项被忽略。"""
        result = parse_custom_data(("invalid_item",))
        assert result == {}

    def test_empty(self):
        """空元组 → 空字典。"""
        result = parse_custom_data(())
        assert result == {}

    def test_value_with_equals(self):
        """value 中包含 '=' 时，只在第一个 '=' 处分割。"""
        result = parse_custom_data(("formula=a=b+c",))
        assert result == {"formula": "a=b+c"}


# ========== format_embed_result ==========

class TestFormatEmbedResult:
    """测试嵌入结果格式化输出（不崩溃即通过）。"""

    def test_success_result(self, capsys):
        """成功结果不崩溃。"""
        result = EmbedResult(
            success=True,
            output_path=Path("/tmp/out.png"),
            message="ok",
            elapsed_time=1.23,
        )
        format_embed_result(result, "test.png")
        captured = capsys.readouterr()
        assert "test.png" in captured.out

    def test_failure_result(self, capsys):
        """失败结果不崩溃。"""
        result = EmbedResult(
            success=False,
            message="Something went wrong",
            elapsed_time=0.5,
        )
        format_embed_result(result, "bad.png")
        captured = capsys.readouterr()
        assert "bad.png" in captured.out


# ========== format_extract_result ==========

class TestFormatExtractResult:
    """测试提取结果格式化输出。"""

    def test_success_result(self, capsys):
        """成功提取结果不崩溃。"""
        payload = WatermarkPayload(employee_id="E001", timestamp="2026-04-05T00:00:00Z")
        result = ExtractResult(success=True, payload=payload, confidence=0.95)
        format_extract_result(result, "file.png", json_mode=False)
        captured = capsys.readouterr()
        assert "E001" in captured.out

    def test_json_mode(self, capsys):
        """json_mode=True 时输出合法 JSON。"""
        payload = WatermarkPayload(employee_id="E002", timestamp="2026-04-05T00:00:00Z")
        result = ExtractResult(success=True, payload=payload, confidence=0.88)
        format_extract_result(result, "file.txt", json_mode=True)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["employee_id"] == "E002"
        assert data["success"] is True

    def test_failure_result(self, capsys):
        """失败提取结果不崩溃。"""
        result = ExtractResult(success=False, message="No watermark found")
        format_extract_result(result, "raw.txt", json_mode=False)
        captured = capsys.readouterr()
        assert "raw.txt" in captured.out


# ========== format_verify_result ==========

class TestFormatVerifyResult:
    """测试验证结果格式化输出。"""

    def test_matched(self, capsys):
        """匹配结果不崩溃。"""
        result = VerifyResult(
            success=True, file_path=Path("/tmp/a.png"),
            employee_id="E001", matched=True, message="Matched: E001",
        )
        format_verify_result(result)
        captured = capsys.readouterr()
        assert "E001" in captured.out

    def test_json_mode(self, capsys):
        """json_mode=True 时输出合法 JSON。"""
        result = VerifyResult(
            success=True, file_path=Path("/tmp/b.txt"),
            employee_id="E003", matched=False, message="Mismatch",
        )
        format_verify_result(result, json_mode=True)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["matched"] is False
