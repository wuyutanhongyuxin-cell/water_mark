"""
CLI 命令集成测试。

使用 Click 的 CliRunner 测试主要命令：
- cli --version / --help
- embed / extract / verify / batch 的 --help
- embed 实际嵌入
- extract 实际提取
- batch --dry-run 列出文件
"""

from pathlib import Path

import pytest
from click.testing import CliRunner

from src.main import cli


@pytest.fixture
def runner():
    """创建 CliRunner，mix_stderr=False 分离 stdout/stderr。"""
    return CliRunner(mix_stderr=False)


# ========== 基本命令测试 ==========

class TestCliBasic:
    """测试 CLI 基础功能（版本、帮助信息）。"""

    def test_version(self, runner):
        """--version 输出版本号。"""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "WatermarkForge" in result.output
        assert "0.7.0" in result.output

    def test_help(self, runner):
        """--help 列出所有子命令。"""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "embed" in result.output
        assert "extract" in result.output
        assert "verify" in result.output
        assert "batch" in result.output

    def test_embed_help(self, runner):
        """embed --help 显示选项说明。"""
        result = runner.invoke(cli, ["embed", "--help"])
        assert result.exit_code == 0
        assert "--input" in result.output
        assert "--employee" in result.output

    def test_extract_help(self, runner):
        """extract --help 显示选项说明。"""
        result = runner.invoke(cli, ["extract", "--help"])
        assert result.exit_code == 0
        assert "--input" in result.output

    def test_verify_help(self, runner):
        """verify --help 显示选项说明。"""
        result = runner.invoke(cli, ["verify", "--help"])
        assert result.exit_code == 0
        assert "--input" in result.output

    def test_batch_help(self, runner):
        """batch --help 显示选项说明。"""
        result = runner.invoke(cli, ["batch", "--help"])
        assert result.exit_code == 0
        assert "--dir" in result.output
        assert "--employee" in result.output


# ========== 实际命令测试 ==========

class TestCliEmbed:
    """测试 embed 命令实际执行。"""

    def test_embed_text_file(self, runner, sample_txt, tmp_path):
        """embed 命令对文本文件嵌入水印。"""
        out_path = tmp_path / "out_cli.txt"
        result = runner.invoke(cli, [
            "embed",
            "-i", str(sample_txt),
            "-e", "E001",
            "-o", str(out_path),
        ])
        # embed 成功时 exit_code=0（通过 SystemExit(0)）
        assert result.exit_code == 0
        assert out_path.exists()

    def test_embed_image_file(self, runner, sample_image, tmp_path):
        """embed 命令对图像文件嵌入水印。"""
        out_path = tmp_path / "out_cli.png"
        result = runner.invoke(cli, [
            "embed",
            "-i", str(sample_image),
            "-e", "E001",
            "-o", str(out_path),
        ])
        assert result.exit_code == 0
        assert out_path.exists()


class TestCliExtract:
    """测试 extract 命令实际执行。"""

    def test_extract_from_watermarked(self, runner, sample_txt, tmp_path):
        """先嵌入，再 extract 提取 → 输出包含 employee 信息。"""
        # 先嵌入
        wm_path = tmp_path / "wm_cli.txt"
        embed_result = runner.invoke(cli, [
            "embed",
            "-i", str(sample_txt),
            "-e", "E001",
            "-o", str(wm_path),
        ])
        assert embed_result.exit_code == 0

        # 再提取
        extract_result = runner.invoke(cli, [
            "extract",
            "-i", str(wm_path),
            "--json",
        ])
        assert extract_result.exit_code == 0
        assert "E001" in extract_result.output


class TestCliBatch:
    """测试 batch 命令。"""

    def test_dry_run(self, runner, tmp_path):
        """--dry-run 模式只列出文件，不实际处理。"""
        # 创建测试文件
        (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
        (tmp_path / "b.txt").write_text("world", encoding="utf-8")

        result = runner.invoke(cli, [
            "batch",
            "-d", str(tmp_path),
            "-e", "E001",
            "--dry-run",
        ])
        assert result.exit_code == 0
        assert "a.txt" in result.output
        assert "b.txt" in result.output
