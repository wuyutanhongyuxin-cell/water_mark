"""
验证模块测试。

测试 src.core.verifier 的独立验证接口：
- verify_file: 单文件验证（有/无预期 ID）
- batch_verify: 批量验证（含错误容错）
"""

from pathlib import Path

import pytest

from src.core.embedder import embed_watermark
from src.core.verifier import verify_file, batch_verify, VerifyResult
from src.watermarks.base import WatermarkPayload, WatermarkStrength


# ========== 辅助 ==========

def _embed(input_path: Path, tmp_path: Path, payload: WatermarkPayload) -> Path:
    """嵌入水印并返回输出路径。"""
    out = tmp_path / f"wm_{input_path.name}"
    result = embed_watermark(input_path, payload, output_path=out)
    assert result.success, f"Embed failed: {result.message}"
    return out


# ========== verify_file 测试 ==========

class TestVerifyFile:
    """测试单文件验证。"""

    def test_watermarked_no_expected_id(
        self, sample_image, sample_payload, tmp_path,
    ):
        """已加水印，不指定预期 ID → success=True, matched=True。"""
        wm_path = _embed(sample_image, tmp_path, sample_payload)
        result = verify_file(wm_path)
        assert result.success is True
        assert result.matched is True
        assert result.employee_id == "E001"

    def test_watermarked_correct_id(
        self, sample_image, sample_payload, tmp_path,
    ):
        """已加水印，指定正确 ID → success=True, matched=True。"""
        wm_path = _embed(sample_image, tmp_path, sample_payload)
        result = verify_file(wm_path, expected_employee_id="E001")
        assert result.success is True
        assert result.matched is True

    def test_watermarked_wrong_id(
        self, sample_image, sample_payload, tmp_path,
    ):
        """已加水印，指定错误 ID → success=True, matched=False。"""
        wm_path = _embed(sample_image, tmp_path, sample_payload)
        result = verify_file(wm_path, expected_employee_id="E999")
        assert result.success is True
        assert result.matched is False

    def test_unwatermarked(self, sample_txt):
        """未加水印 → success=False。"""
        result = verify_file(sample_txt)
        assert result.success is False


# ========== batch_verify 测试 ==========

class TestBatchVerify:
    """测试批量验证。"""

    def test_batch_multiple_files(
        self, sample_image, sample_txt, sample_payload, tmp_path,
    ):
        """批量验证多个文件 → 返回列表，长度正确。"""
        wm_img = _embed(sample_image, tmp_path, sample_payload)
        wm_txt = _embed(sample_txt, tmp_path, sample_payload)
        results = batch_verify([wm_img, wm_txt])
        assert len(results) == 2
        assert all(isinstance(r, VerifyResult) for r in results)
        assert all(r.success for r in results)

    def test_batch_error_isolation(
        self, sample_image, sample_payload, tmp_path,
    ):
        """批量验证中一个文件出错不影响其他文件。"""
        wm_img = _embed(sample_image, tmp_path, sample_payload)
        bad_path = tmp_path / "nonexistent.txt"
        results = batch_verify([wm_img, bad_path])
        assert len(results) == 2
        # 第一个应成功
        assert results[0].success is True
        # 第二个应失败但不抛异常
        assert results[1].success is False
