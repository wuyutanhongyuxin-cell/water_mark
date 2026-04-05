"""
目录扫描模块测试。

测试 src.cli.scan 的目录扫描功能：
- get_supported_extensions: 从 rules 加载支持的扩展名
- scan_directory: 扫描目录，过滤隐藏文件/不支持类型
- scan_summary: 按类别统计
- _is_hidden: 隐藏文件检测
"""

from pathlib import Path

import pytest

from src.cli.scan import (
    get_supported_extensions,
    scan_directory,
    scan_summary,
    _is_hidden,
)


# ========== get_supported_extensions ==========

class TestGetSupportedExtensions:
    """测试支持的扩展名读取。"""

    def test_includes_common_types(self):
        """应包含常见文件类型。"""
        exts = get_supported_extensions()
        assert ".jpg" in exts
        assert ".png" in exts
        assert ".pdf" in exts
        assert ".txt" in exts
        assert ".docx" in exts
        assert ".xlsx" in exts
        assert ".wav" in exts

    def test_returns_set(self):
        """返回值应为 set 类型。"""
        exts = get_supported_extensions()
        assert isinstance(exts, set)

    def test_excludes_unknown(self):
        """不应包含 unknown 类别的扩展名。"""
        exts = get_supported_extensions()
        # unknown 类别没有 extensions 字段
        assert ".xyz" not in exts


# ========== _is_hidden ==========

class TestIsHidden:
    """测试隐藏文件检测。"""

    def test_hidden_file(self):
        """以 . 开头的文件名 → True。"""
        assert _is_hidden(Path(".hidden_file.txt")) is True

    def test_hidden_dir(self):
        """父目录以 . 开头 → True。"""
        assert _is_hidden(Path(".git/config")) is True

    def test_normal_file(self):
        """普通文件 → False。"""
        assert _is_hidden(Path("docs/readme.txt")) is False


# ========== scan_directory ==========

class TestScanDirectory:
    """测试目录扫描功能。"""

    @pytest.fixture
    def scan_dir(self, tmp_path):
        """创建测试目录结构。"""
        # 支持的文件
        (tmp_path / "image.jpg").write_bytes(b"\xff\xd8\xff\xe0dummy")
        (tmp_path / "doc.txt").write_text("hello", encoding="utf-8")
        (tmp_path / "report.pdf").write_bytes(b"%PDF-1.4 dummy")

        # 不支持的文件
        (tmp_path / "unknown.xyz").write_text("skip me")

        # 隐藏文件
        (tmp_path / ".hidden_file.txt").write_text("hidden")

        # 子目录
        sub = tmp_path / "subdir"
        sub.mkdir()
        (sub / "nested.png").write_bytes(b"\x89PNG\r\n\x1a\ndummy")

        return tmp_path

    def test_finds_supported_files(self, scan_dir):
        """扫描到支持的文件类型。"""
        files = scan_directory(scan_dir, recursive=True)
        names = {f.name for f in files}
        assert "image.jpg" in names
        assert "doc.txt" in names
        assert "report.pdf" in names

    def test_skips_hidden(self, scan_dir):
        """跳过隐藏文件。"""
        files = scan_directory(scan_dir, recursive=True)
        names = {f.name for f in files}
        assert ".hidden_file.txt" not in names

    def test_recursive_true(self, scan_dir):
        """recursive=True 时扫描子目录。"""
        files = scan_directory(scan_dir, recursive=True)
        names = {f.name for f in files}
        assert "nested.png" in names

    def test_recursive_false(self, scan_dir):
        """recursive=False 时只扫描根目录。"""
        files = scan_directory(scan_dir, recursive=False)
        names = {f.name for f in files}
        assert "nested.png" not in names

    def test_nonexistent_dir(self, tmp_path):
        """不存在的目录 → 空列表。"""
        result = scan_directory(tmp_path / "no_such_dir")
        assert result == []

    def test_excludes_unsupported(self, scan_dir):
        """不支持的扩展名被过滤。"""
        files = scan_directory(scan_dir, recursive=True)
        names = {f.name for f in files}
        assert "unknown.xyz" not in names


# ========== scan_summary ==========

class TestScanSummary:
    """测试扫描统计。"""

    def test_counts_by_category(self, tmp_path):
        """按类别统计文件数量。"""
        # 创建几个测试文件
        (tmp_path / "a.jpg").write_bytes(b"dummy")
        (tmp_path / "b.png").write_bytes(b"dummy")
        (tmp_path / "c.txt").write_text("hi")

        files = [
            tmp_path / "a.jpg",
            tmp_path / "b.png",
            tmp_path / "c.txt",
        ]
        result = scan_summary(files)
        # jpg 和 png 都属于 image 类别
        assert result.get("image", 0) == 2
        assert result.get("text", 0) == 1
