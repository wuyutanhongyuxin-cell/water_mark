"""
水印基类模块测试。

测试 src.watermarks.base 的数据结构、枚举、抽象基类。
"""

from pathlib import Path

import pytest

from src.watermarks.base import (
    EmbedResult,
    ExtractResult,
    WatermarkBase,
    WatermarkPayload,
    WatermarkStrength,
)


# ========== WatermarkStrength 枚举 ==========

def test_strength_enum_values():
    """三个强度等级的值应与预期一致。"""
    assert WatermarkStrength.LOW.value == "low"
    assert WatermarkStrength.MEDIUM.value == "medium"
    assert WatermarkStrength.HIGH.value == "high"


def test_strength_from_value():
    """可以通过字符串值构造枚举成员。"""
    assert WatermarkStrength("low") == WatermarkStrength.LOW
    assert WatermarkStrength("medium") == WatermarkStrength.MEDIUM
    assert WatermarkStrength("high") == WatermarkStrength.HIGH


def test_strength_invalid_value():
    """非法值应抛出 ValueError。"""
    with pytest.raises(ValueError):
        WatermarkStrength("ultra")


# ========== WatermarkPayload 数据类 ==========

def test_payload_auto_timestamp():
    """未提供 timestamp 时，__post_init__ 应自动填充 UTC 时间。"""
    payload = WatermarkPayload(employee_id="E001")
    # 自动生成的时间戳不应为空
    assert payload.timestamp != ""
    # 应为 ISO 8601 格式，以 Z 结尾
    assert payload.timestamp.endswith("Z")
    assert "T" in payload.timestamp


def test_payload_keeps_provided_timestamp():
    """显式提供 timestamp 时，应保留原值不覆盖。"""
    ts = "2026-01-01T12:00:00Z"
    payload = WatermarkPayload(employee_id="E002", timestamp=ts)
    assert payload.timestamp == ts


def test_payload_default_custom_data():
    """custom_data 默认应为空字典。"""
    payload = WatermarkPayload(employee_id="E003")
    assert payload.custom_data == {}
    assert isinstance(payload.custom_data, dict)


def test_payload_custom_data_independent():
    """不同实例的 custom_data 应互相独立（field default_factory 验证）。"""
    p1 = WatermarkPayload(employee_id="E001")
    p2 = WatermarkPayload(employee_id="E002")
    p1.custom_data["key"] = "value"
    # p2 的 custom_data 不应受 p1 影响
    assert "key" not in p2.custom_data


# ========== EmbedResult 数据类 ==========

def test_embed_result_defaults():
    """EmbedResult 默认值应正确初始化。"""
    result = EmbedResult(success=True)

    assert result.success is True
    assert result.output_path is None
    assert result.message == ""
    assert result.quality_metrics == {}
    assert result.elapsed_time == 0.0


def test_embed_result_with_values():
    """EmbedResult 带完整参数的初始化。"""
    p = Path("/tmp/output.png")
    result = EmbedResult(
        success=True,
        output_path=p,
        message="OK",
        quality_metrics={"psnr": 42.0},
        elapsed_time=1.5,
    )
    assert result.output_path == p
    assert result.quality_metrics["psnr"] == 42.0


# ========== ExtractResult 数据类 ==========

def test_extract_result_defaults():
    """ExtractResult 默认值应正确初始化。"""
    result = ExtractResult(success=False)

    assert result.success is False
    assert result.payload is None
    assert result.confidence == 0.0
    assert result.message == ""


# ========== WatermarkBase 抽象基类 ==========

def test_base_cannot_instantiate():
    """直接实例化抽象基类应抛出 TypeError。"""
    with pytest.raises(TypeError):
        WatermarkBase()  # type: ignore[abstract]


def test_subclass_must_implement_abstracts():
    """子类未实现所有抽象方法时，实例化应抛出 TypeError。"""
    # 只实现 embed，缺少 extract 和 supported_extensions
    class PartialWM(WatermarkBase):
        def embed(self, input_path, payload, output_path):
            pass

    with pytest.raises(TypeError):
        PartialWM()  # type: ignore[abstract]


def test_subclass_full_implementation():
    """完整实现所有抽象方法的子类应能正常实例化。"""
    class DummyWM(WatermarkBase):
        def embed(self, input_path, payload, output_path):
            return EmbedResult(success=True)

        def extract(self, file_path):
            return ExtractResult(success=False)

        def supported_extensions(self):
            return [".dummy"]

    wm = DummyWM(strength=WatermarkStrength.HIGH)
    assert wm.strength == WatermarkStrength.HIGH
    assert wm.supported_extensions() == [".dummy"]


def test_subclass_default_strength():
    """子类不传 strength 时，默认应为 MEDIUM。"""
    class DummyWM(WatermarkBase):
        def embed(self, input_path, payload, output_path):
            return EmbedResult(success=True)

        def extract(self, file_path):
            return ExtractResult(success=False)

        def supported_extensions(self):
            return [".test"]

    wm = DummyWM()
    assert wm.strength == WatermarkStrength.MEDIUM
