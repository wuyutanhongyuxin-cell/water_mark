"""
图像盲水印处理器测试（DWT-DCT-SVD）。

测试 ImageWatermark 的嵌入/提取往返、质量指标、
不同强度对比、小图像边界情况。
"""

import cv2
import pytest

from src.watermarks.base import WatermarkStrength, WatermarkPayload
from src.watermarks.image_wm import ImageWatermark


# ========== 辅助函数 ==========


def _make_processor(strength: WatermarkStrength = WatermarkStrength.MEDIUM):
    """创建指定强度的图像水印处理器。"""
    return ImageWatermark(strength=strength)


# ========== 嵌入→提取往返测试 ==========


class TestImageRoundtrip:
    """嵌入后提取，验证水印载荷一致性。"""

    def test_embed_extract_roundtrip(self, sample_image, sample_payload, tmp_path):
        """嵌入水印后提取，employee_id 应一致。"""
        wm = _make_processor()
        output = tmp_path / "output.png"

        # 嵌入
        embed_result = wm.embed(sample_image, sample_payload, output)
        assert embed_result.success, f"Embed failed: {embed_result.message}"

        # 提取并校验核心字段
        extract_result = wm.extract(output)
        assert extract_result.success, f"Extract failed: {extract_result.message}"
        assert extract_result.payload is not None
        assert extract_result.payload.employee_id == "E001"

    def test_output_file_exists_and_readable(self, sample_image, sample_payload, tmp_path):
        """输出文件存在且可被 OpenCV 正常读取。"""
        wm = _make_processor()
        output = tmp_path / "output.png"
        wm.embed(sample_image, sample_payload, output)

        # 文件存在
        assert output.exists()

        # cv2 可正常读取
        img = cv2.imread(str(output))
        assert img is not None
        assert img.shape[0] > 0 and img.shape[1] > 0


# ========== 质量指标测试 ==========


class TestQualityMetrics:
    """验证嵌入结果中的质量指标。"""

    def test_embed_result_has_psnr(self, sample_image, sample_payload, tmp_path):
        """EmbedResult.quality_metrics 应包含 psnr 键。"""
        wm = _make_processor()
        output = tmp_path / "output.png"
        result = wm.embed(sample_image, sample_payload, output)

        assert result.success
        assert "psnr" in result.quality_metrics
        # PSNR 应为正数（合理范围 20~60dB）
        assert result.quality_metrics["psnr"] > 0

    def test_different_strengths_produce_different_psnr(
        self, sample_image, sample_payload, tmp_path,
    ):
        """
        不同强度的 PSNR 应有差异：
        LOW（低嵌入量）→ 最高 PSNR
        HIGH（高嵌入量）→ 最低 PSNR
        """
        psnr_by_strength = {}
        for strength in [WatermarkStrength.LOW, WatermarkStrength.MEDIUM, WatermarkStrength.HIGH]:
            wm = ImageWatermark(strength=strength)
            output = tmp_path / f"output_{strength.value}.png"
            result = wm.embed(sample_image, sample_payload, output)
            assert result.success, f"Embed failed at {strength.value}: {result.message}"
            psnr_by_strength[strength] = result.quality_metrics["psnr"]

        # LOW 强度 PSNR 最高（对图像改动最小）
        assert psnr_by_strength[WatermarkStrength.LOW] > psnr_by_strength[WatermarkStrength.MEDIUM]
        # MEDIUM 强度 PSNR 高于 HIGH
        assert psnr_by_strength[WatermarkStrength.MEDIUM] > psnr_by_strength[WatermarkStrength.HIGH]


# ========== 支持扩展名测试 ==========


class TestSupportedExtensions:
    """验证 supported_extensions 返回正确的格式列表。"""

    def test_supported_extensions(self):
        """应包含常见图像格式。"""
        wm = _make_processor()
        exts = wm.supported_extensions()

        for ext in [".png", ".jpg", ".bmp", ".webp"]:
            assert ext in exts, f"{ext} should be in supported_extensions"


# ========== 边界情况测试 ==========


class TestEdgeCases:
    """小图像等边界场景。"""

    def test_small_image_embed(self, small_image, sample_payload, tmp_path):
        """
        100x100 小图像嵌入：blind-watermark 的 block_num 不足以容纳 1024-bit，
        应抛出 AssertionError（库内部限制）。通过 pytest.raises 确认预期行为。
        """
        wm = _make_processor()
        output = tmp_path / "small_output.png"

        # blind-watermark 对小图抛 AssertionError（block_num < wm_size）
        with pytest.raises(AssertionError):
            wm.embed(small_image, sample_payload, output)
