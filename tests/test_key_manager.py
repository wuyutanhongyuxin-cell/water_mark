"""
密钥管理模块测试。

测试 src.security.key_manager 的密钥生成、保存、加载、优先级获取逻辑。
"""

import os
from pathlib import Path

import pytest

from src.security.crypto import KEY_LENGTH
from src.security.key_manager import (
    _ENV_KEY_NAME,
    _load_key_from_env,
    generate_key,
    get_key,
    load_key,
    save_key,
)


# ========== 密钥生成 ==========

def test_generate_key_length():
    """生成的密钥应为 32 字节。"""
    key = generate_key()
    assert isinstance(key, bytes)
    assert len(key) == KEY_LENGTH


def test_generate_key_randomness():
    """两次生成的密钥不应相同。"""
    k1 = generate_key()
    k2 = generate_key()
    assert k1 != k2


# ========== 保存-加载往返 ==========

def test_save_load_roundtrip(tmp_path):
    """保存密钥后加载，内容应完全一致。"""
    key = generate_key()
    save_key(key, key_id=0, key_dir=tmp_path)

    loaded = load_key(key_id=0, key_dir=tmp_path)
    assert loaded == key


def test_save_creates_file(tmp_path):
    """save_key 应在目录下创建正确的 .key 文件。"""
    key = generate_key()
    path = save_key(key, key_id=5, key_dir=tmp_path)

    assert path == tmp_path / "key_005.key"
    assert path.exists()
    # 文件内容是 hex 编码
    assert path.read_text(encoding="utf-8") == key.hex()


# ========== 加载：文件不存在 ==========

def test_load_key_nonexistent(tmp_path):
    """加载不存在的密钥文件应返回 None。"""
    result = load_key(key_id=999, key_dir=tmp_path)
    assert result is None


# ========== 加载：文件内容损坏（非法 hex） ==========

def test_load_key_corrupt_hex(tmp_path):
    """密钥文件内容不是有效 hex，应返回 None。"""
    key_path = tmp_path / "key_000.key"
    key_path.write_text("not-valid-hex-content!", encoding="utf-8")

    result = load_key(key_id=0, key_dir=tmp_path)
    assert result is None


# ========== 加载：hex 有效但长度错误 ==========

def test_load_key_wrong_length(tmp_path):
    """密钥文件 hex 可解码但不是 32 字节，应返回 None。"""
    key_path = tmp_path / "key_000.key"
    # 16 字节 = 32 字符 hex（不是 32 字节 = 64 字符 hex）
    key_path.write_text("aa" * 16, encoding="utf-8")

    result = load_key(key_id=0, key_dir=tmp_path)
    assert result is None


# ========== get_key 优先级 1：环境变量 ==========

def test_get_key_env_priority(tmp_path):
    """环境变量已设置时，get_key 应返回环境变量中的密钥。
    注意：autouse 的 fixed_key fixture 已设置了 WATERMARK_MASTER_KEY="a"*64
    """
    # "a" * 64 hex → 0xAA...AA = b'\xaa' * 32
    expected = bytes.fromhex("a" * 64)

    result = get_key(key_id=0, key_dir=tmp_path)
    assert result == expected


# ========== get_key 优先级 2：密钥文件 ==========

def test_get_key_file_priority(monkeypatch, tmp_path):
    """无环境变量但有文件时，应返回文件中的密钥。"""
    # 移除环境变量（autouse fixture 已设置）
    monkeypatch.delenv(_ENV_KEY_NAME, raising=False)

    file_key = generate_key()
    save_key(file_key, key_id=0, key_dir=tmp_path)

    result = get_key(key_id=0, key_dir=tmp_path, auto_generate=False)
    assert result == file_key


# ========== get_key 优先级 3：自动生成 ==========

def test_get_key_auto_generate(monkeypatch, tmp_path):
    """无环境变量、无文件时，auto_generate=True 应自动生成新密钥。"""
    monkeypatch.delenv(_ENV_KEY_NAME, raising=False)

    result = get_key(key_id=0, key_dir=tmp_path, auto_generate=True)

    # 应返回有效的 32 字节密钥
    assert result is not None
    assert len(result) == KEY_LENGTH
    # 密钥应同时被保存到文件
    assert (tmp_path / "key_000.key").exists()


# ========== get_key：auto_generate=False 且无密钥 → None ==========

def test_get_key_no_auto_generate_returns_none(monkeypatch, tmp_path):
    """Lesson #12：auto_generate=False 且无可用密钥时应返回 None。"""
    monkeypatch.delenv(_ENV_KEY_NAME, raising=False)

    result = get_key(key_id=0, key_dir=tmp_path, auto_generate=False)
    assert result is None


# ========== _load_key_from_env：无效 hex ==========

def test_load_key_from_env_invalid_hex(monkeypatch):
    """环境变量中的值不是有效 hex，应返回 None。"""
    monkeypatch.setenv(_ENV_KEY_NAME, "this_is_not_hex!")

    result = _load_key_from_env()
    assert result is None


# ========== _load_key_from_env：hex 有效但长度错误 ==========

def test_load_key_from_env_wrong_length(monkeypatch):
    """环境变量 hex 有效但解码后不是 32 字节，应返回 None。"""
    # 16 字节的 hex = "bb" * 16
    monkeypatch.setenv(_ENV_KEY_NAME, "bb" * 16)

    result = _load_key_from_env()
    assert result is None
