"""
AES-256-GCM 水印载荷加密模块。

加密：plaintext → nonce(12B) + ciphertext + tag(16B)
解密：反向过程，认证失败返回 None（不抛异常）
"""

import os
from typing import Optional

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from loguru import logger

# AES-256 密钥长度：32 字节
KEY_LENGTH = 32
# GCM nonce 长度：12 字节（NIST 推荐）
NONCE_LENGTH = 12
# GCM 认证标签长度：16 字节（AESGCM 默认）
TAG_LENGTH = 16
# 加密开销：nonce + tag = 28 字节
OVERHEAD = NONCE_LENGTH + TAG_LENGTH


def encrypt_payload(plaintext: bytes, key: bytes) -> bytes:
    """
    AES-256-GCM 加密水印载荷。

    Args:
        plaintext: 明文字节（水印 JSON）
        key: 32 字节 AES-256 密钥

    Returns:
        bytes: nonce(12B) + ciphertext + tag(16B)

    Raises:
        ValueError: 密钥格式无效
    """
    if not validate_key(key):
        raise ValueError("Invalid key format")

    # 每次加密生成随机 nonce（确保相同明文不会产生相同密文）
    nonce = os.urandom(NONCE_LENGTH)
    aesgcm = AESGCM(key)
    # encrypt() 返回 ciphertext + tag（tag 自动附加在末尾）
    ct_with_tag = aesgcm.encrypt(nonce, plaintext, None)

    return nonce + ct_with_tag


def decrypt_payload(cipherdata: bytes, key: bytes) -> Optional[bytes]:
    """
    AES-256-GCM 解密水印载荷。

    认证失败（密钥错误或密文被篡改）时返回 None，不抛异常。

    Args:
        cipherdata: nonce(12B) + ciphertext + tag(16B)
        key: 32 字节 AES-256 密钥

    Returns:
        Optional[bytes]: 解密后的明文，失败返回 None
    """
    if not validate_key(key):
        logger.warning("Decryption failed: invalid key format")
        return None

    # 最短有效密文：nonce(12) + 至少 1 字节密文 + tag(16) = 29 字节
    if len(cipherdata) < OVERHEAD + 1:
        logger.warning(f"Cipherdata too short: {len(cipherdata)} bytes")
        return None

    nonce = cipherdata[:NONCE_LENGTH]
    ct_with_tag = cipherdata[NONCE_LENGTH:]

    try:
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ct_with_tag, None)
        return plaintext
    except InvalidTag:
        # GCM 认证失败：密钥错误或数据被篡改
        logger.warning("Decryption failed: authentication tag mismatch")
        return None
    except Exception:
        logger.warning("Decryption failed: unexpected error")
        return None


def validate_key(key: bytes) -> bool:
    """校验 AES-256 密钥格式：必须是 32 字节 bytes。"""
    return isinstance(key, bytes) and len(key) == KEY_LENGTH
