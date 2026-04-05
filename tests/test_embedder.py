"""
嵌入模块测试。

测试 src.core.embedder 的统一嵌入接口：
- 正常嵌入（图像、文本）
- 自动验证（auto_verify）
- 输出路径安全检查（输出 != 输入）
- 文件不存在 / 非文件 / 找不到处理器
- 回滚机制（嵌入失败时删除输出文件）
- output_dir 指定输出目录
"""

from pathlib import Path

import pytest

from src.core.embedder import embed_watermark, _build_output_path
from src.watermarks.base import WatermarkPayload, WatermarkStrength, EmbedResult


# ========== _build_output_path 工具函数 ==========

class TestBuildOutputPath:
    """测试输出路径生成逻辑。"""

    def test_default_dir(self, tmp_path):
        """output_dir=None 时，输出到原文件同目录。"""
        input_path = tmp_path / "report.pdf"
        result = _build_output_path(input_path, None, "{stem}_wm{ext}")
        assert result == tmp_path / "report_wm.pdf"

    def test_custom_dir(self, tmp_path):
        """指定 output_dir 时，输出到该目录。"""
        input_path = tmp_path / "report.pdf"
        out_dir = tmp_path / "output"
        result = _build_output_path(input_path, out_dir, "{stem}_wm{ext}")
        assert result == out_dir / "report_wm.pdf"
        # 目录应被自动创建
        assert out_dir.exists()

    def test_custom_naming(self, tmp_path):
        """自定义命名模板。"""
        input_path = tmp_path / "data.txt"
        result = _build_output_path(input_path, None, "{stem}_marked{ext}")
        assert result.name == "data_marked.txt"


# ========== embed_watermark 正常流程 ==========

class TestEmbedHappyPath:
    """测试正常嵌入流程。"""

    def test_image_embed(self, sample_image, sample_payload, tmp_path):
        """图像嵌入：success=True，输出文件存在。"""
        out_path = tmp_path / "out_image.png"
        result = embed_watermark(
            input_path=sample_image,
            payload=sample_payload,
            output_path=out_path,
        )
        assert result.success is True
        assert out_path.exists()
        assert out_path.stat().st_size > 0

    def test_text_embed(self, sample_txt, sample_payload, tmp_path):
        """文本嵌入：success=True。"""
        out_path = tmp_path / "out_text.txt"
        result = embed_watermark(
            input_path=sample_txt,
            payload=sample_payload,
            output_path=out_path,
        )
        assert result.success is True
        assert out_path.exists()

    def test_auto_verify_runs_by_default(self, sample_txt, sample_payload, tmp_path):
        """auto_verify=True（默认）时，验证流程自动运行。
        如果嵌入 + 验证都成功，说明 auto_verify 正常工作。"""
        out_path = tmp_path / "verified.txt"
        result = embed_watermark(
            input_path=sample_txt,
            payload=sample_payload,
            output_path=out_path,
            auto_verify=True,
        )
        assert result.success is True


# ========== embed_watermark 错误处理 ==========

class TestEmbedErrors:
    """测试嵌入时的各种错误情况。"""

    def test_output_equals_input(self, sample_txt, sample_payload):
        """输出路径 == 输入路径 → 报"rollback safety"错误。"""
        result = embed_watermark(
            input_path=sample_txt,
            payload=sample_payload,
            output_path=sample_txt,  # 故意和输入相同
        )
        assert result.success is False
        assert "rollback safety" in result.message.lower()

    def test_file_not_found(self, tmp_path, sample_payload):
        """输入文件不存在 → success=False。"""
        fake_path = tmp_path / "nonexistent.txt"
        result = embed_watermark(
            input_path=fake_path,
            payload=sample_payload,
        )
        assert result.success is False
        assert "not found" in result.message.lower()

    def test_directory_not_file(self, tmp_path, sample_payload):
        """输入是目录而非文件 → success=False。"""
        result = embed_watermark(
            input_path=tmp_path,  # 目录
            payload=sample_payload,
        )
        assert result.success is False
        assert "not a file" in result.message.lower()

    def test_rollback_on_failure(self, sample_txt, sample_payload, tmp_path):
        """嵌入失败时，输出文件应被回滚（删除）。
        使用一个无法路由的文件格式来触发失败。"""
        bad_file = tmp_path / "test.xyz"
        bad_file.write_text("dummy content")
        out_path = tmp_path / "should_not_exist.xyz"
        result = embed_watermark(
            input_path=bad_file,
            payload=sample_payload,
            output_path=out_path,
        )
        assert result.success is False
        # 输出文件不应存在（已回滚或从未创建）
        assert not out_path.exists()

    def test_output_dir_specified(self, sample_txt, sample_payload, tmp_path):
        """指定 output_dir 时，输出到该目录。"""
        out_dir = tmp_path / "custom_output"
        result = embed_watermark(
            input_path=sample_txt,
            payload=sample_payload,
            output_dir=out_dir,
        )
        assert result.success is True
        # 输出文件应在 output_dir 下
        assert result.output_path is not None
        assert result.output_path.parent == out_dir
