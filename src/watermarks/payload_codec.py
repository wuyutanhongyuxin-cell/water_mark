"""
水印载荷编解码器（v1/v2 格式）。

v2 格式（1024-bit）：[version 1B][key_id 1B][encrypted_len 1B][AES-GCM 密文][padding]
v1 格式（512-bit）：明文 JSON + 0x00 填充（Phase 2 遗留兼容）

关键设计：用 encrypted_len 字段精确截取密文，避免 rstrip(b'\\x00') 误删末尾零字节。
"""

import json
from typing import Optional

from loguru import logger

from src.watermarks.base import WatermarkPayload

# === v2 载荷编码：128 字节 = 1024 bits ===
_PAYLOAD_BYTES = 128
_PAYLOAD_BITS = _PAYLOAD_BYTES * 8
PAYLOAD_BITS = _PAYLOAD_BITS   # 公开导出供外部模块引用

# v1 遗留参数（回退提取用）
_LEGACY_PAYLOAD_BITS = 64 * 8  # 512 bits

# v2 格式头部: [version 1B][key_id 1B][encrypted_len 1B]
_VERSION_V2 = 0x02
_HEADER_SIZE = 3


def payload_to_bits(payload: WatermarkPayload) -> list[int]:
    """将 WatermarkPayload 序列化为 1024-bit 加密数组（v2 格式）。"""
    # 1. 序列化为压缩 JSON
    data = {"e": payload.employee_id, "t": payload.timestamp, "h": payload.file_hash}
    json_bytes = json.dumps(data, separators=(",", ":")).encode("utf-8")

    # 2. AES-256-GCM 加密
    from src.security.crypto import encrypt_payload
    from src.security.key_manager import get_key
    key_id = 0
    key = get_key(key_id=key_id)
    encrypted = encrypt_payload(json_bytes, key)

    # 3. 组装 v2: [version][key_id][encrypted_len][encrypted][zero-padding]
    max_data = _PAYLOAD_BYTES - _HEADER_SIZE
    if len(encrypted) > max_data:
        raise ValueError(
            f"Encrypted payload too large: {len(encrypted)}B > {max_data}B"
        )
    buf = bytearray(_PAYLOAD_BYTES)
    buf[0] = _VERSION_V2
    buf[1] = key_id
    buf[2] = len(encrypted)  # 精确长度，避免 rstrip(b'\x00') 误删
    buf[_HEADER_SIZE:_HEADER_SIZE + len(encrypted)] = encrypted

    # 4. 每字节展开为 8 bits（大端序）
    return bytes_to_bits(buf)


def bits_to_payload(bits: list[int]) -> Optional[WatermarkPayload]:
    """将 1024-bit 数组反序列化为 WatermarkPayload。自动识别 v1/v2。"""
    # 长度校验：期望 1024 bits，过短则跳过（防止垃圾数据进入解码流程）
    if len(bits) < _HEADER_SIZE * 8:
        logger.warning(f"Bit array too short: {len(bits)} < {_HEADER_SIZE * 8}")
        return None
    raw = bits_to_bytes(bits)
    # v2 格式：首字节 == 0x02
    if len(raw) >= _HEADER_SIZE and raw[0] == _VERSION_V2:
        return _decode_v2(raw)
    # 回退尝试 v1 明文 JSON
    return decode_v1_json(raw)


def _decode_v2(raw: bytes) -> Optional[WatermarkPayload]:
    """解码 v2 加密格式。用 encrypted_len 精确截取密文。"""
    key_id = raw[1]
    encrypted_len = raw[2]
    if encrypted_len == 0 or _HEADER_SIZE + encrypted_len > len(raw):
        return None
    # 精确截取（不用 rstrip，避免误删密文末尾零字节）
    encrypted = raw[_HEADER_SIZE:_HEADER_SIZE + encrypted_len]
    try:
        from src.security.crypto import decrypt_payload
        from src.security.key_manager import get_key
        # 提取时禁止自动生成密钥（防止恶意 key_id 创建文件）
        key = get_key(key_id=key_id, auto_generate=False)
        if key is None:
            logger.warning(f"No key found for key_id={key_id} during extraction")
            return None
        plaintext = decrypt_payload(encrypted, key)
        if plaintext is None:
            return None
        data = json.loads(plaintext.decode("utf-8"))
        return WatermarkPayload(
            employee_id=data.get("e", ""),
            timestamp=data.get("t", ""),
            file_hash=data.get("h", ""),
        )
    except Exception as e:
        logger.warning(f"v2 decode failed: {e}")
        return None


def decode_v1_json(raw: bytes) -> Optional[WatermarkPayload]:
    """解码 v1 明文 JSON 格式（Phase 2 兼容）。"""
    json_bytes = bytes(raw).rstrip(b"\x00")
    try:
        data = json.loads(json_bytes.decode("utf-8"))
        return WatermarkPayload(
            employee_id=data.get("e", ""),
            timestamp=data.get("t", ""),
            file_hash=data.get("h", ""),
        )
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def bytes_to_bits(data: bytes) -> list[int]:
    """字节序列 → bit 数组（大端序）。"""
    bits = []
    for byte_val in data:
        for i in range(7, -1, -1):
            bits.append((byte_val >> i) & 1)
    return bits


def bits_to_bytes(bits: list[int]) -> bytes:
    """bit 数组 → 字节序列。"""
    raw = bytearray()
    for i in range(0, len(bits), 8):
        byte_val = 0
        for j in range(8):
            if i + j < len(bits):
                byte_val = (byte_val << 1) | bits[i + j]
        raw.append(byte_val)
    return bytes(raw)
