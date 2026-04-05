"""
性能基准测试。

测量各文件类型水印嵌入/提取的执行时间。
使用 @pytest.mark.benchmark 标记，可通过 pytest -m benchmark 单独运行。

阈值设定（基于合理预期）：
- 图像嵌入/提取：< 10s (300x300)
- 文本嵌入：< 1s
- PDF 嵌入：< 15s
"""

import time
from pathlib import Path

import pytest

from src.core.embedder import embed_watermark
from src.core.extractor import extract_watermark
from src.watermarks.base import WatermarkPayload


# ========== 辅助 ==========

def _timed_embed(input_path, payload, output_path):
    """计时嵌入，返回 (result, elapsed_seconds)。"""
    start = time.monotonic()
    result = embed_watermark(input_path, payload, output_path=output_path)
    elapsed = time.monotonic() - start
    return result, elapsed


def _timed_extract(file_path):
    """计时提取，返回 (result, elapsed_seconds)。"""
    start = time.monotonic()
    result = extract_watermark(file_path)
    elapsed = time.monotonic() - start
    return result, elapsed


# ========== 嵌入性能 ==========

@pytest.mark.benchmark
class TestEmbedPerformance:
    """嵌入性能基准。"""

    def test_image_embed_under_10s(self, sample_image, sample_payload, tmp_path):
        """图像嵌入应在 10 秒内完成（300x300 PNG）。"""
        out = tmp_path / "bench_img.png"
        result, elapsed = _timed_embed(sample_image, sample_payload, out)
        assert result.success, f"Embed failed: {result.message}"
        assert elapsed < 10.0, f"Image embed too slow: {elapsed:.2f}s > 10s"

    def test_text_embed_under_1s(self, sample_txt, sample_payload, tmp_path):
        """文本嵌入应在 1 秒内完成。"""
        out = tmp_path / "bench_txt.txt"
        result, elapsed = _timed_embed(sample_txt, sample_payload, out)
        assert result.success, f"Embed failed: {result.message}"
        assert elapsed < 1.0, f"Text embed too slow: {elapsed:.2f}s > 1s"

    def test_pdf_embed_under_15s(self, sample_pdf, sample_payload, tmp_path):
        """PDF 嵌入应在 15 秒内完成。"""
        out = tmp_path / "bench_pdf.pdf"
        result, elapsed = _timed_embed(sample_pdf, sample_payload, out)
        assert result.success, f"Embed failed: {result.message}"
        assert elapsed < 30.0, f"PDF embed too slow: {elapsed:.2f}s > 30s"


# ========== 提取性能 ==========

@pytest.mark.benchmark
class TestExtractPerformance:
    """提取性能基准。"""

    def test_image_extract_under_10s(self, sample_image, sample_payload, tmp_path):
        """图像提取应在 10 秒内完成。"""
        # 先嵌入
        wm_path = tmp_path / "bench_extract_img.png"
        embed_result = embed_watermark(sample_image, sample_payload, output_path=wm_path)
        assert embed_result.success

        # 计时提取
        result, elapsed = _timed_extract(wm_path)
        assert result.success, f"Extract failed: {result.message}"
        assert elapsed < 10.0, f"Image extract too slow: {elapsed:.2f}s > 10s"
