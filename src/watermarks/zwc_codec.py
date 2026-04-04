"""
零宽字符（ZWC）编解码器。

将 1024-bit 载荷编码为不可见的零宽 Unicode 字符序列，
嵌入文本文件后肉眼不可见。text_wm 和 office_wm 共用此模块。

协议: [ZWJ 开始标记][1024 个 ZWC 字符][WJ 结束标记]
"""

from typing import Optional

from loguru import logger

# 零宽字符映射
ZWC_BIT_0 = "\u200B"   # Zero Width Space → bit 0
ZWC_BIT_1 = "\u200C"   # Zero Width Non-Joiner → bit 1
ZWC_START = "\u200D"    # Zero Width Joiner → 开始标记
ZWC_END = "\u2060"      # Word Joiner → 结束标记

# 所有 ZWC 字符集合（用于 strip 操作）
_ZWC_CHARS = frozenset({ZWC_BIT_0, ZWC_BIT_1, ZWC_START, ZWC_END})

# 载荷长度（与 payload_codec 一致）
_EXPECTED_BITS = 1024


def zwc_encode(bits: list[int]) -> str:
    """
    将 bit 数组编码为零宽字符串。

    Args:
        bits: 1024 个 0/1 整数组成的列表

    Returns:
        str: [ZWC_START][编码字符][ZWC_END] 格式的不可见字符串

    Raises:
        ValueError: bits 长度不是 1024
    """
    if len(bits) != _EXPECTED_BITS:
        raise ValueError(f"Expected {_EXPECTED_BITS} bits, got {len(bits)}")
    chars = [ZWC_START]
    for b in bits:
        chars.append(ZWC_BIT_1 if b else ZWC_BIT_0)
    chars.append(ZWC_END)
    return "".join(chars)


def zwc_decode(text: str) -> Optional[list[int]]:
    """
    从文本中扫描并解码零宽字符水印。

    在文本中查找 ZWC_START...ZWC_END 标记对，
    提取中间的 bit 序列。

    Args:
        text: 可能包含零宽字符水印的文本

    Returns:
        1024 个 0/1 组成的列表，未找到则返回 None
    """
    start_idx = text.find(ZWC_START)
    if start_idx == -1:
        return None
    end_idx = text.find(ZWC_END, start_idx + 1)
    if end_idx == -1:
        return None
    # 提取标记之间的字符
    block = text[start_idx + 1:end_idx]
    bits = []
    for ch in block:
        if ch == ZWC_BIT_0:
            bits.append(0)
        elif ch == ZWC_BIT_1:
            bits.append(1)
        # 忽略其他字符（容错）
    if len(bits) != _EXPECTED_BITS:
        logger.warning(f"ZWC decode: expected {_EXPECTED_BITS} bits, got {len(bits)}")
        return None
    return bits


def strip_zwc(text: str) -> str:
    """
    移除文本中所有零宽字符（测试/调试用）。

    Args:
        text: 可能含有零宽字符的文本

    Returns:
        str: 清除所有 ZWC 字符后的文本
    """
    return "".join(ch for ch in text if ch not in _ZWC_CHARS)
