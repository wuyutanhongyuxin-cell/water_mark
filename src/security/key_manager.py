"""
密钥管理模块。

支持三种密钥来源（优先级从高到低）：
1. 环境变量 WATERMARK_MASTER_KEY（hex 编码）
2. 密钥文件 config/keys/key_XXX.key
3. 自动生成新密钥并保存到文件
"""

import os
from pathlib import Path
from typing import Optional

from loguru import logger

from src.security.crypto import KEY_LENGTH

# 默认密钥存储目录
_DEFAULT_KEY_DIR = Path(__file__).parent.parent.parent / "config" / "keys"
# 环境变量名
_ENV_KEY_NAME = "WATERMARK_MASTER_KEY"


def generate_key() -> bytes:
    """生成随机 32 字节 AES-256 密钥。"""
    key = os.urandom(KEY_LENGTH)
    logger.info("Generated new AES-256 key")
    return key


def save_key(
    key: bytes, key_id: int = 0, key_dir: Path = _DEFAULT_KEY_DIR,
) -> Path:
    """
    保存密钥到文件（hex 编码，方便人工检查）。

    文件路径: {key_dir}/key_{key_id:03d}.key

    Args:
        key: 32 字节密钥
        key_id: 密钥编号（0-999）
        key_dir: 密钥存储目录

    Returns:
        Path: 保存的文件路径
    """
    key_dir.mkdir(parents=True, exist_ok=True)
    key_path = key_dir / f"key_{key_id:03d}.key"
    key_path.write_text(key.hex(), encoding="utf-8")
    logger.info(f"Saved key {key_id} to {key_path}")
    return key_path


def load_key(
    key_id: int = 0, key_dir: Path = _DEFAULT_KEY_DIR,
) -> Optional[bytes]:
    """
    从文件加载密钥。

    Args:
        key_id: 密钥编号
        key_dir: 密钥存储目录

    Returns:
        Optional[bytes]: 密钥字节，文件不存在或格式错误返回 None
    """
    key_path = key_dir / f"key_{key_id:03d}.key"
    if not key_path.exists():
        return None
    try:
        hex_str = key_path.read_text(encoding="utf-8").strip()
        key = bytes.fromhex(hex_str)
        if len(key) != KEY_LENGTH:
            logger.error(
                f"Key file corrupted: expected {KEY_LENGTH} bytes, "
                f"got {len(key)}"
            )
            return None
        return key
    except (ValueError, OSError) as e:
        logger.error(f"Failed to load key {key_id}: {e}")
        return None


def _load_key_from_env() -> Optional[bytes]:
    """从环境变量加载密钥（hex 编码）。"""
    hex_str = os.environ.get(_ENV_KEY_NAME, "").strip()
    if not hex_str:
        return None
    try:
        key = bytes.fromhex(hex_str)
        if len(key) != KEY_LENGTH:
            logger.error(
                f"Env key invalid: expected {KEY_LENGTH} bytes, "
                f"got {len(key)}"
            )
            return None
        logger.info("Loaded key from environment variable")
        return key
    except ValueError:
        logger.error(f"Env key {_ENV_KEY_NAME} is not valid hex")
        return None


def get_key(
    key_id: int = 0, key_dir: Path = _DEFAULT_KEY_DIR,
    auto_generate: bool = True,
) -> Optional[bytes]:
    """
    获取密钥（统一入口）。

    优先级：环境变量 > 密钥文件 > 自动生成（仅 auto_generate=True 时）。

    Args:
        key_id: 密钥编号
        key_dir: 密钥存储目录
        auto_generate: 是否在密钥不存在时自动生成。
            嵌入时应为 True，提取时应为 False（防止恶意 key_id 创建文件）。

    Returns:
        bytes: 32 字节 AES-256 密钥。auto_generate=False 且密钥不存在时返回 None。
    """
    # 1. 尝试环境变量
    key = _load_key_from_env()
    if key:
        return key

    # 2. 尝试密钥文件
    key = load_key(key_id, key_dir)
    if key:
        return key

    # 3. 自动生成并保存（仅嵌入场景允许）
    if not auto_generate:
        logger.warning(f"No key found for id={key_id}, auto_generate=False")
        return None
    logger.warning(f"No key found for id={key_id}, generating new key")
    key = generate_key()
    save_key(key, key_id, key_dir)
    return key
