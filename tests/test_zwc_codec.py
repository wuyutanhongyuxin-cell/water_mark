"""
零宽字符编解码器测试。

测试 src.watermarks.zwc_codec 的 ZWC 编码/解码/清除功能。
"""

import pytest

from src.watermarks.zwc_codec import (
    ZWC_BIT_0,
    ZWC_BIT_1,
    ZWC_END,
    ZWC_START,
    _EXPECTED_BITS,
    strip_zwc,
    zwc_decode,
    zwc_encode,
)


# ========== 编解码往返 ==========

def test_encode_decode_roundtrip():
    """zwc_encode → zwc_decode 往返，bit 数组应完全一致。"""
    # 构造 1024 位的交替 bit 模式
    bits = [i % 2 for i in range(1024)]
    encoded = zwc_encode(bits)
    decoded = zwc_decode(encoded)

    assert decoded == bits


# ========== 编码格式：起止标记 ==========

def test_encoded_starts_and_ends_with_markers():
    """编码字符串应以 ZWC_START 开头、ZWC_END 结尾。"""
    bits = [0] * 1024
    encoded = zwc_encode(bits)

    assert encoded[0] == ZWC_START
    assert encoded[-1] == ZWC_END


# ========== 编码长度 ==========

def test_encoded_length():
    """编码字符串长度应为 1024（bit 字符）+ 2（标记）= 1026。"""
    bits = [1] * 1024
    encoded = zwc_encode(bits)

    assert len(encoded) == _EXPECTED_BITS + 2


# ========== 编码：bit 数量错误 ==========

def test_wrong_bit_count_raises():
    """bit 数组长度不是 1024 时应抛出 ValueError。"""
    with pytest.raises(ValueError, match="Expected 1024"):
        zwc_encode([0] * 100)

    with pytest.raises(ValueError, match="Expected 1024"):
        zwc_encode([1] * 2048)

    with pytest.raises(ValueError, match="Expected 1024"):
        zwc_encode([])


# ========== strip_zwc：清除 ZWC 字符 ==========

def test_strip_zwc_removes_all():
    """strip_zwc 应移除所有四种零宽字符。"""
    bits = [0, 1, 0, 1] * 256  # 1024 bits
    encoded = zwc_encode(bits)
    # 在正常文本中间插入编码后的 ZWC
    mixed = "Hello" + encoded + "World"

    result = strip_zwc(mixed)
    assert result == "HelloWorld"


# ========== strip_zwc：纯文本不变 ==========

def test_strip_zwc_normal_text():
    """不含 ZWC 的普通文本，strip_zwc 应原样返回。"""
    text = "This is normal text with no hidden chars."
    assert strip_zwc(text) == text


# ========== 解码：无标记 ==========

def test_decode_no_markers():
    """文本中无 ZWC_START/ZWC_END 标记，应返回 None。"""
    result = zwc_decode("plain text with no watermark")
    assert result is None


# ========== 解码：bit 数量不匹配 ==========

def test_decode_wrong_bit_count():
    """标记之间的 bit 数不是 1024，应返回 None。"""
    # 手工构造：起始标记 + 10 个 bit 字符 + 结束标记
    short_payload = ZWC_START + ZWC_BIT_0 * 10 + ZWC_END
    result = zwc_decode(short_payload)

    assert result is None


# ========== 解码：嵌入在正常文本中 ==========

def test_decode_embedded_in_text():
    """ZWC 水印嵌入在正常文本中间，应能正确提取。"""
    bits = [1, 0] * 512  # 1024 bits
    encoded = zwc_encode(bits)
    text_with_wm = "前缀文本" + encoded + "后缀文本"

    decoded = zwc_decode(text_with_wm)
    assert decoded == bits
