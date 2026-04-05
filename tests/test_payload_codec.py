"""
水印载荷编解码器测试。

测试 src.watermarks.payload_codec 的 v1/v2 编解码、bit/byte 互转。
"""

import json

import pytest

from src.watermarks.base import WatermarkPayload
from src.watermarks.payload_codec import (
    PAYLOAD_BITS,
    _LEGACY_PAYLOAD_BITS,
    _VERSION_V2,
    bits_to_bytes,
    bits_to_payload,
    bytes_to_bits,
    decode_v1_json,
    payload_to_bits,
)


# ========== v2 编解码往返 ==========

def test_payload_roundtrip(sample_payload):
    """payload_to_bits → bits_to_payload 往返，关键字段应一致。"""
    bits = payload_to_bits(sample_payload)
    result = bits_to_payload(bits)

    assert result is not None
    assert result.employee_id == sample_payload.employee_id
    assert result.timestamp == sample_payload.timestamp


# ========== 输出长度 ==========

def test_output_exactly_1024_bits(sample_payload):
    """编码结果应恰好 1024 bits。"""
    bits = payload_to_bits(sample_payload)
    assert len(bits) == PAYLOAD_BITS
    assert PAYLOAD_BITS == 1024


# ========== bit 值合法性 ==========

def test_all_bits_are_binary(sample_payload):
    """所有 bit 值必须是 0 或 1。"""
    bits = payload_to_bits(sample_payload)
    for b in bits:
        assert b in (0, 1), f"非法 bit 值: {b}"


# ========== bytes ↔ bits 往返 ==========

def test_bytes_bits_roundtrip():
    """bytes_to_bits → bits_to_bytes 往返，数据应完全一致。"""
    original = b"\x00\xff\x55\xaa\x01\x80"
    bits = bytes_to_bits(original)
    restored = bits_to_bytes(bits)
    assert restored == original


def test_bytes_to_bits_known_value():
    """已知值验证：0xA5 = 10100101。"""
    bits = bytes_to_bits(b"\xa5")
    assert bits == [1, 0, 1, 0, 0, 1, 0, 1]


# ========== v2 格式标识 ==========

def test_v2_format_first_byte(sample_payload):
    """v2 格式的原始数据首字节应为 0x02。"""
    bits = payload_to_bits(sample_payload)
    raw = bits_to_bytes(bits)
    assert raw[0] == _VERSION_V2  # 0x02


# ========== v1 兼容解码 ==========

def test_v1_legacy_decode():
    """手工构造 v1 明文 JSON 格式，decode_v1_json 应能正确解码。"""
    # v1 格式：压缩 JSON + 0x00 填充
    data = {"e": "E999", "t": "2026-01-01T00:00:00Z", "h": "deadbeef"}
    json_bytes = json.dumps(data, separators=(",", ":")).encode("utf-8")
    # 填充到 64 字节（v1 载荷大小）
    padded = json_bytes + b"\x00" * (64 - len(json_bytes))

    result = decode_v1_json(padded)

    assert result is not None
    assert result.employee_id == "E999"
    assert result.timestamp == "2026-01-01T00:00:00Z"
    assert result.file_hash == "deadbeef"


# ========== v1 解码失败 ==========

def test_v1_decode_garbage():
    """非法 JSON 数据，decode_v1_json 应返回 None。"""
    result = decode_v1_json(b"\xff\xfe\xfd" + b"\x00" * 61)
    assert result is None


# ========== bits_to_payload：输入太短 ==========

def test_bits_too_short_returns_none():
    """bit 数组太短（< header 最小长度），应返回 None。"""
    # 少于 3 字节 = 24 bits 的数据
    result = bits_to_payload([0] * 10)
    assert result is None


# ========== bits_to_payload：全零垃圾数据 ==========

def test_all_zeros_returns_none():
    """1024 个全零 bit（垃圾数据），应返回 None。"""
    result = bits_to_payload([0] * 1024)
    # 首字节 = 0x00，不是 v2 标识，回退 v1 → JSON 解析失败 → None
    assert result is None


# ========== 载荷过大 ==========

def test_very_long_employee_id_raises():
    """employee_id 过长导致加密载荷超过容量限制，应抛出 ValueError。"""
    # 128 字节减去头部(3B)和加密开销(28B) = 97B 可用空间
    # JSON 格式 {"e":"...","t":"...","h":"..."} 本身约 30+ 字节
    # 很长的 employee_id 会超过限制
    long_id = "X" * 200
    payload = WatermarkPayload(
        employee_id=long_id,
        timestamp="2026-01-01T00:00:00Z",
        file_hash="abcdef1234567890",
    )
    with pytest.raises(ValueError, match="too large"):
        payload_to_bits(payload)


# ========== PAYLOAD_BITS 和 _LEGACY_PAYLOAD_BITS 常量 ==========

def test_payload_bits_constant():
    """公开常量 PAYLOAD_BITS 应为 1024。"""
    assert PAYLOAD_BITS == 1024


def test_legacy_payload_bits_constant():
    """v1 遗留常量应为 512。"""
    assert _LEGACY_PAYLOAD_BITS == 512


# ========== bits_to_bytes 空输入 ==========

def test_bits_to_bytes_empty():
    """空 bit 列表应返回空 bytes。"""
    assert bits_to_bytes([]) == b""


# ========== bytes_to_bits 空输入 ==========

def test_bytes_to_bits_empty():
    """空 bytes 应返回空列表。"""
    assert bytes_to_bits(b"") == []
