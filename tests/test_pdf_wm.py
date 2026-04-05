"""
PDF 盲水印处理器测试（渲染→噪声预处理→DWT-DCT-SVD→重建）。

测试 PdfWatermark 的嵌入/提取往返、输出 PDF 完整性、
页数保持、空白 PDF 拒绝、支持格式列表。
"""

import fitz  # PyMuPDF
import pytest

from src.watermarks.base import WatermarkStrength
from src.watermarks.pdf_wm import PdfWatermark


# ========== 辅助函数 ==========


def _make_processor():
    """创建 PDF 水印处理器。"""
    return PdfWatermark(strength=WatermarkStrength.MEDIUM)


def _create_empty_pdf(path):
    """创建一个近似空的 PDF 文件（PyMuPDF 不允许保存 0 页，用最小化手段）。"""
    # PyMuPDF 不支持保存 0 页 PDF，直接写入最简 PDF 结构
    path.write_bytes(
        b"%PDF-1.0\n1 0 obj<</Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\n"
        b"xref\n0 3\n0000000000 65535 f \n"
        b"0000000009 00000 n \n0000000045 00000 n \n"
        b"trailer<</Root 1 0 R/Size 3>>\nstartxref\n92\n%%EOF"
    )


# ========== 嵌入→提取往返测试 ==========


class TestPdfRoundtrip:
    """嵌入后提取，验证水印载荷一致性。"""

    def test_embed_extract_roundtrip(self, sample_pdf, sample_payload, tmp_path):
        """PDF 嵌入→提取，employee_id 应一致。"""
        wm = _make_processor()
        output = tmp_path / "output.pdf"

        embed_result = wm.embed(sample_pdf, sample_payload, output)
        assert embed_result.success, f"Embed failed: {embed_result.message}"

        extract_result = wm.extract(output)
        assert extract_result.success, f"Extract failed: {extract_result.message}"
        assert extract_result.payload is not None
        assert extract_result.payload.employee_id == "E001"


# ========== 输出 PDF 完整性测试 ==========


class TestPdfIntegrity:
    """输出 PDF 文件应可正常打开且结构完整。"""

    def test_output_openable_with_fitz(self, sample_pdf, sample_payload, tmp_path):
        """输出 PDF 可用 PyMuPDF 正常打开。"""
        wm = _make_processor()
        output = tmp_path / "output.pdf"
        wm.embed(sample_pdf, sample_payload, output)

        # PyMuPDF 正常打开，不抛异常
        doc = fitz.open(str(output))
        assert doc.page_count > 0
        doc.close()

    def test_output_page_count_matches(self, sample_pdf, sample_payload, tmp_path):
        """输出 PDF 页数应与输入一致。"""
        wm = _make_processor()
        output = tmp_path / "output.pdf"

        # 获取输入 PDF 页数
        input_doc = fitz.open(str(sample_pdf))
        input_pages = input_doc.page_count
        input_doc.close()

        wm.embed(sample_pdf, sample_payload, output)

        # 输出页数应相同
        output_doc = fitz.open(str(output))
        assert output_doc.page_count == input_pages
        output_doc.close()


# ========== 边界情况测试 ==========


class TestEdgeCases:
    """空白 PDF 等边界场景。"""

    def test_empty_pdf_fails(self, sample_payload, tmp_path):
        """0 页 PDF 嵌入应失败，不崩溃。"""
        wm = _make_processor()
        empty_pdf = tmp_path / "empty.pdf"
        _create_empty_pdf(empty_pdf)
        output = tmp_path / "output.pdf"

        result = wm.embed(empty_pdf, sample_payload, output)
        assert not result.success
        # 错误信息应提到 "no pages" 或类似内容
        assert "page" in result.message.lower() or "empty" in result.message.lower()


# ========== 支持扩展名测试 ==========


class TestSupportedExtensions:
    """验证 supported_extensions 返回正确的格式列表。"""

    def test_supported_extensions(self):
        """应仅包含 .pdf 格式。"""
        wm = _make_processor()
        exts = wm.supported_extensions()
        assert exts == [".pdf"]
