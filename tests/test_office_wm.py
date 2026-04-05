"""
Office 文档水印处理器测试（DOCX/XLSX/PPTX）。

测试 OfficeWatermark 对三种 Office 格式的嵌入/提取往返、
输出文件可用对应库正常打开、支持格式列表。
"""

import pytest

from src.watermarks.base import WatermarkStrength
from src.watermarks.office_wm import OfficeWatermark


# ========== 辅助函数 ==========


def _make_processor():
    """创建 Office 水印处理器。"""
    return OfficeWatermark(strength=WatermarkStrength.MEDIUM)


# ========== DOCX 测试 ==========


class TestDocxWatermark:
    """DOCX 文件水印嵌入/提取测试。"""

    def test_docx_roundtrip(self, sample_docx, sample_payload, tmp_path):
        """DOCX 嵌入→提取，employee_id 应一致。"""
        wm = _make_processor()
        output = tmp_path / "output.docx"

        embed_result = wm.embed(sample_docx, sample_payload, output)
        assert embed_result.success, f"Embed failed: {embed_result.message}"

        extract_result = wm.extract(output)
        assert extract_result.success, f"Extract failed: {extract_result.message}"
        assert extract_result.payload is not None
        assert extract_result.payload.employee_id == "E001"

    def test_docx_output_openable(self, sample_docx, sample_payload, tmp_path):
        """嵌入水印后的 DOCX 可用 python-docx 正常打开。"""
        import docx

        wm = _make_processor()
        output = tmp_path / "output.docx"
        wm.embed(sample_docx, sample_payload, output)

        # python-docx 正常打开，不抛异常
        document = docx.Document(str(output))
        # 至少有一个段落（原文内容未丢失）
        assert len(document.paragraphs) > 0


# ========== XLSX 测试 ==========


class TestXlsxWatermark:
    """XLSX 文件水印嵌入/提取测试。"""

    def test_xlsx_roundtrip(self, sample_xlsx, sample_payload, tmp_path):
        """XLSX 嵌入→提取，employee_id 应一致。"""
        wm = _make_processor()
        output = tmp_path / "output.xlsx"

        embed_result = wm.embed(sample_xlsx, sample_payload, output)
        assert embed_result.success, f"Embed failed: {embed_result.message}"

        extract_result = wm.extract(output)
        assert extract_result.success, f"Extract failed: {extract_result.message}"
        assert extract_result.payload is not None
        assert extract_result.payload.employee_id == "E001"

    def test_xlsx_output_openable(self, sample_xlsx, sample_payload, tmp_path):
        """嵌入水印后的 XLSX 可用 openpyxl 正常打开。"""
        import openpyxl

        wm = _make_processor()
        output = tmp_path / "output.xlsx"
        wm.embed(sample_xlsx, sample_payload, output)

        # openpyxl 正常打开，不抛异常
        wb = openpyxl.load_workbook(str(output))
        ws = wb.active
        # 至少有数据（原文内容未丢失）
        assert ws.max_row >= 1
        wb.close()


# ========== PPTX 测试 ==========


class TestPptxWatermark:
    """PPTX 文件水印嵌入/提取测试。"""

    def test_pptx_roundtrip(self, sample_pptx, sample_payload, tmp_path):
        """PPTX 嵌入→提取，employee_id 应一致。"""
        wm = _make_processor()
        output = tmp_path / "output.pptx"

        embed_result = wm.embed(sample_pptx, sample_payload, output)
        assert embed_result.success, f"Embed failed: {embed_result.message}"

        extract_result = wm.extract(output)
        assert extract_result.success, f"Extract failed: {extract_result.message}"
        assert extract_result.payload is not None
        assert extract_result.payload.employee_id == "E001"

    def test_pptx_output_openable(self, sample_pptx, sample_payload, tmp_path):
        """嵌入水印后的 PPTX 可用 python-pptx 正常打开。"""
        from pptx import Presentation

        wm = _make_processor()
        output = tmp_path / "output.pptx"
        wm.embed(sample_pptx, sample_payload, output)

        # python-pptx 正常打开，不抛异常
        prs = Presentation(str(output))
        # 至少有一张幻灯片（内容未丢失）
        assert len(prs.slides) > 0


# ========== 支持扩展名测试 ==========


class TestSupportedExtensions:
    """验证 supported_extensions 返回正确的格式列表。"""

    def test_supported_extensions(self):
        """应包含 .docx / .xlsx / .pptx 三种格式。"""
        wm = _make_processor()
        exts = wm.supported_extensions()
        assert exts == [".docx", ".xlsx", ".pptx"]
