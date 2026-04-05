"""
提取模块测试。

测试 src.core.extractor 的统一提取接口：
- 从已加水印文件提取 → 获取正确载荷
- 从未加水印文件提取 → success=False
- 文件不存在 / 非文件
- verify_watermark 员工 ID 比对
"""

from pathlib import Path

import pytest

from src.core.embedder import embed_watermark
from src.core.extractor import extract_watermark, verify_watermark
from src.watermarks.base import WatermarkPayload, WatermarkStrength


# ========== 辅助：先嵌入再提取 ==========

def _embed_file(input_path: Path, tmp_path: Path, payload: WatermarkPayload) -> Path:
    """嵌入水印并返回输出文件路径。"""
    out_path = tmp_path / f"wm_{input_path.name}"
    result = embed_watermark(
        input_path=input_path,
        payload=payload,
        output_path=out_path,
    )
    assert result.success, f"Embed failed: {result.message}"
    return out_path


# ========== extract_watermark 测试 ==========

class TestExtractWatermark:
    """测试水印提取功能。"""

    def test_extract_from_watermarked_image(
        self, sample_image, sample_payload, tmp_path,
    ):
        """从已加水印的图像中提取 → success=True，employee_id 一致。"""
        wm_path = _embed_file(sample_image, tmp_path, sample_payload)
        result = extract_watermark(wm_path)
        assert result.success is True
        assert result.payload is not None
        assert result.payload.employee_id == "E001"

    def test_extract_from_watermarked_text(
        self, sample_txt, sample_payload, tmp_path,
    ):
        """从已加水印的文本中提取 → success=True。"""
        wm_path = _embed_file(sample_txt, tmp_path, sample_payload)
        result = extract_watermark(wm_path)
        assert result.success is True
        assert result.payload is not None
        assert result.payload.employee_id == "E001"

    def test_extract_from_unwatermarked(self, sample_txt):
        """从未加水印的文件提取 → success=False。"""
        result = extract_watermark(sample_txt)
        assert result.success is False

    def test_file_not_found(self, tmp_path):
        """文件不存在 → success=False。"""
        fake = tmp_path / "ghost.png"
        result = extract_watermark(fake)
        assert result.success is False
        assert "not found" in result.message.lower()

    def test_not_a_file(self, tmp_path):
        """传入目录 → success=False。"""
        result = extract_watermark(tmp_path)
        assert result.success is False
        assert "not a file" in result.message.lower()


# ========== verify_watermark 测试 ==========

class TestVerifyWatermark:
    """测试便捷验证函数（比对 employee_id）。"""

    def test_verify_correct_id(self, sample_image, sample_payload, tmp_path):
        """正确的 employee_id → True。"""
        wm_path = _embed_file(sample_image, tmp_path, sample_payload)
        assert verify_watermark(wm_path, "E001") is True

    def test_verify_wrong_id(self, sample_image, sample_payload, tmp_path):
        """错误的 employee_id → False。"""
        wm_path = _embed_file(sample_image, tmp_path, sample_payload)
        assert verify_watermark(wm_path, "E999") is False

    def test_verify_unwatermarked(self, sample_txt):
        """未加水印的文件 → False。"""
        assert verify_watermark(sample_txt, "E001") is False
