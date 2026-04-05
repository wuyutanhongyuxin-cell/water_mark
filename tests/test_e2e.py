"""
端到端集成测试。

完整的 嵌入 → 提取 → 验证 链路测试，覆盖所有文件类型。
每个测试确认：
1. embed_watermark 成功
2. extract_watermark 能提取到正确的 employee_id
3. verify_file 验证通过
"""

from pathlib import Path

import pytest
from click.testing import CliRunner

from src.core.embedder import embed_watermark
from src.core.extractor import extract_watermark
from src.core.verifier import verify_file, batch_verify, VerifyResult
from src.watermarks.base import WatermarkPayload, WatermarkStrength
from src.main import cli


# ========== 辅助函数 ==========

def _full_roundtrip(
    input_path: Path, tmp_path: Path, payload: WatermarkPayload,
) -> None:
    """执行完整的 嵌入 → 提取 → 验证 链路，断言每步成功。"""
    out_path = tmp_path / f"e2e_{input_path.name}"

    # 1. 嵌入
    embed_result = embed_watermark(
        input_path=input_path,
        payload=payload,
        output_path=out_path,
    )
    assert embed_result.success, f"Embed failed: {embed_result.message}"
    assert out_path.exists(), "Output file not created"

    # 2. 提取
    extract_result = extract_watermark(out_path)
    assert extract_result.success, f"Extract failed: {extract_result.message}"
    assert extract_result.payload is not None, "Payload is None"
    assert extract_result.payload.employee_id == payload.employee_id, (
        f"ID mismatch: expected={payload.employee_id}, "
        f"got={extract_result.payload.employee_id}"
    )

    # 3. 验证
    verify_result = verify_file(out_path, expected_employee_id=payload.employee_id)
    assert verify_result.success, f"Verify failed: {verify_result.message}"
    assert verify_result.matched, (
        f"Verify ID mismatch: {verify_result.message}"
    )


# ========== 各文件类型 E2E ==========

class TestImageE2E:
    """图像文件端到端测试。"""

    def test_png_roundtrip(self, sample_image, sample_payload, tmp_path):
        """PNG: 嵌入 → 提取 → 验证。"""
        _full_roundtrip(sample_image, tmp_path, sample_payload)


class TestTextE2E:
    """文本文件端到端测试。"""

    def test_txt_roundtrip(self, sample_txt, sample_payload, tmp_path):
        """TXT: 嵌入 → 提取 → 验证。"""
        _full_roundtrip(sample_txt, tmp_path, sample_payload)

    def test_csv_roundtrip(self, sample_csv, sample_payload, tmp_path):
        """CSV: 嵌入 → 提取 → 验证。"""
        _full_roundtrip(sample_csv, tmp_path, sample_payload)

    def test_json_roundtrip(self, sample_json, sample_payload, tmp_path):
        """JSON: 嵌入 → 提取 → 验证。"""
        _full_roundtrip(sample_json, tmp_path, sample_payload)

    def test_md_roundtrip(self, sample_md, sample_payload, tmp_path):
        """Markdown: 嵌入 → 提取 → 验证。"""
        _full_roundtrip(sample_md, tmp_path, sample_payload)


class TestPdfE2E:
    """PDF 文件端到端测试。"""

    def test_pdf_roundtrip(self, sample_pdf, sample_payload, tmp_path):
        """PDF: 嵌入 → 提取 → 验证。"""
        _full_roundtrip(sample_pdf, tmp_path, sample_payload)


class TestDocxE2E:
    """DOCX 文件端到端测试。"""

    def test_docx_roundtrip(self, sample_docx, sample_payload, tmp_path):
        """DOCX: 嵌入 → 提取 → 验证。"""
        _full_roundtrip(sample_docx, tmp_path, sample_payload)


class TestXlsxE2E:
    """XLSX 文件端到端测试。"""

    def test_xlsx_roundtrip(self, sample_xlsx, sample_payload, tmp_path):
        """XLSX: 嵌入 → 提取 → 验证。"""
        _full_roundtrip(sample_xlsx, tmp_path, sample_payload)


class TestPptxE2E:
    """PPTX 文件端到端测试。"""

    def test_pptx_roundtrip(self, sample_pptx, sample_payload, tmp_path):
        """PPTX: 嵌入 → 提取 → 验证。"""
        _full_roundtrip(sample_pptx, tmp_path, sample_payload)


# ========== 批量验证 E2E ==========

class TestBatchE2E:
    """批量验证端到端测试。"""

    def test_batch_verify_multiple(
        self, sample_image, sample_txt, sample_payload, tmp_path,
    ):
        """多文件批量验证。"""
        # 嵌入多个文件
        wm_img = tmp_path / "e2e_batch_img.png"
        wm_txt = tmp_path / "e2e_batch_txt.txt"

        r1 = embed_watermark(sample_image, sample_payload, output_path=wm_img)
        r2 = embed_watermark(sample_txt, sample_payload, output_path=wm_txt)
        assert r1.success and r2.success

        # 批量验证
        results = batch_verify(
            [wm_img, wm_txt],
            expected_employee_id="E001",
        )
        assert len(results) == 2
        assert all(r.success and r.matched for r in results)


# ========== CLI E2E ==========

class TestCliE2E:
    """通过 CLI 命令进行端到端测试。"""

    def test_cli_embed_extract_roundtrip(self, sample_txt, tmp_path):
        """CLI: embed → extract 往返测试。"""
        runner = CliRunner(mix_stderr=False)
        wm_path = tmp_path / "cli_e2e.txt"

        # 嵌入
        embed_res = runner.invoke(cli, [
            "embed",
            "-i", str(sample_txt),
            "-e", "E001",
            "-o", str(wm_path),
        ])
        assert embed_res.exit_code == 0, f"Embed failed: {embed_res.output}"

        # 提取（JSON 模式）
        extract_res = runner.invoke(cli, [
            "extract",
            "-i", str(wm_path),
            "--json",
        ])
        assert extract_res.exit_code == 0, f"Extract failed: {extract_res.output}"
        assert "E001" in extract_res.output

    def test_cli_verify_roundtrip(self, sample_image, tmp_path):
        """CLI: embed → verify 往返测试。"""
        runner = CliRunner(mix_stderr=False)
        wm_path = tmp_path / "cli_verify.png"

        # 嵌入
        embed_res = runner.invoke(cli, [
            "embed",
            "-i", str(sample_image),
            "-e", "E001",
            "-o", str(wm_path),
        ])
        assert embed_res.exit_code == 0

        # 验证
        verify_res = runner.invoke(cli, [
            "verify",
            "-i", str(wm_path),
            "-e", "E001",
        ])
        assert verify_res.exit_code == 0
