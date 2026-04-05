"""
AES-256-GCM 加密模块测试。

测试 src.security.crypto 的加密/解密/密钥校验功能。
"""

import os

import pytest

from src.security.crypto import (
    KEY_LENGTH,
    NONCE_LENGTH,
    OVERHEAD,
    TAG_LENGTH,
    decrypt_payload,
    encrypt_payload,
    validate_key,
)


# ========== 常量校验 ==========

def test_constants():
    """验证常量值与 AES-256-GCM 规范一致。"""
    assert KEY_LENGTH == 32
    assert NONCE_LENGTH == 12
    assert TAG_LENGTH == 16
    assert OVERHEAD == NONCE_LENGTH + TAG_LENGTH  # 28


# ========== 加密-解密往返 ==========

def test_encrypt_decrypt_roundtrip():
    """加密后解密，明文应完全一致。"""
    key = os.urandom(32)
    plaintext = b"watermark payload test data"

    cipherdata = encrypt_payload(plaintext, key)
    result = decrypt_payload(cipherdata, key)

    assert result == plaintext


# ========== 错误密钥 ==========

def test_wrong_key_returns_none():
    """用错误密钥解密，应返回 None（不抛异常）。"""
    key_a = os.urandom(32)
    key_b = os.urandom(32)
    plaintext = b"secret data"

    cipherdata = encrypt_payload(plaintext, key_a)
    # 用 key_b 解密 key_a 加密的数据
    result = decrypt_payload(cipherdata, key_b)

    assert result is None


# ========== 篡改密文 ==========

def test_tampered_cipherdata_returns_none():
    """篡改密文后解密，GCM 认证失败应返回 None。"""
    key = os.urandom(32)
    plaintext = b"integrity check"

    cipherdata = encrypt_payload(plaintext, key)
    # 翻转密文中间的一个字节
    tampered = bytearray(cipherdata)
    mid = len(tampered) // 2
    tampered[mid] ^= 0xFF
    result = decrypt_payload(bytes(tampered), key)

    assert result is None


# ========== validate_key：正确 32 字节 ==========

def test_validate_key_correct():
    """32 字节 bytes 应返回 True。"""
    assert validate_key(os.urandom(32)) is True


# ========== validate_key：长度错误 ==========

def test_validate_key_wrong_length():
    """非 32 字节应返回 False。"""
    assert validate_key(b"short") is False
    assert validate_key(os.urandom(16)) is False
    assert validate_key(os.urandom(64)) is False


# ========== validate_key：非 bytes 类型 ==========

def test_validate_key_not_bytes():
    """非 bytes 类型应返回 False。"""
    assert validate_key("a" * 32) is False  # type: ignore[arg-type]
    assert validate_key(123) is False        # type: ignore[arg-type]
    assert validate_key(None) is False       # type: ignore[arg-type]


# ========== nonce 随机性 ==========

def test_same_plaintext_different_ciphertext():
    """相同明文+密钥，两次加密结果不同（nonce 随机性保证）。"""
    key = os.urandom(32)
    plaintext = b"duplicate test"

    ct1 = encrypt_payload(plaintext, key)
    ct2 = encrypt_payload(plaintext, key)

    # 密文不应相同（概率极低可忽略）
    assert ct1 != ct2
    # 但两者都能正确解密
    assert decrypt_payload(ct1, key) == plaintext
    assert decrypt_payload(ct2, key) == plaintext


# ========== 密文太短 ==========

def test_cipherdata_too_short_returns_none():
    """密文长度 < OVERHEAD + 1 时应返回 None。"""
    key = os.urandom(32)
    # 刚好 OVERHEAD 字节（缺少密文体），应返回 None
    assert decrypt_payload(b"\x00" * OVERHEAD, key) is None
    # 空数据也应返回 None
    assert decrypt_payload(b"", key) is None


# ========== 无效密钥格式触发 ValueError ==========

def test_invalid_key_raises_valueerror_on_encrypt():
    """加密时传入无效密钥应抛出 ValueError。"""
    with pytest.raises(ValueError, match="Invalid key format"):
        encrypt_payload(b"data", b"short_key")

    with pytest.raises(ValueError, match="Invalid key format"):
        encrypt_payload(b"data", "not_bytes")  # type: ignore[arg-type]
