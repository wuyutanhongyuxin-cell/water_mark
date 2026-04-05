"""
视频盲水印处理器测试（逐帧 DWT-DCT-SVD + 多数表决提取）。

测试 VideoWatermark 的嵌入/提取往返、质量指标、
输出视频可读、frame_interval 校验、小尺寸视频拒绝、格式列表。
标记为 slow：视频处理耗时较长。
"""

import cv2
import numpy as np
import pytest

from src.watermarks.base import WatermarkStrength
from src.watermarks.video_wm import VideoWatermark


# ========== 辅助函数 ==========


def _make_processor(frame_interval: int = 10):
    """创建视频水印处理器。"""
    return VideoWatermark(
        strength=WatermarkStrength.MEDIUM,
        frame_interval=frame_interval,
    )


def _create_tiny_avi(path, width=64, height=64, n_frames=10):
    """
    创建尺寸极小的 AVI 视频（低于 _MIN_FRAME_SIZE=256）。
    用于测试小尺寸拒绝逻辑。
    """
    fourcc = cv2.VideoWriter_fourcc(*"FFV1")
    writer = cv2.VideoWriter(str(path), fourcc, 10.0, (width, height))
    rng = np.random.RandomState(7)
    for _ in range(n_frames):
        frame = rng.randint(0, 256, (height, width, 3), dtype=np.uint8)
        writer.write(frame)
    writer.release()


# ========== 嵌入→提取往返测试 ==========


@pytest.mark.slow
class TestVideoRoundtrip:
    """嵌入后提取，验证水印载荷一致性。"""

    def test_avi_roundtrip(self, sample_avi, sample_payload, tmp_path):
        """
        AVI 嵌入→提取，employee_id 应一致。
        sample_avi 为 320x320、20 帧，frame_interval=10 → 嵌入 2 帧。
        """
        wm = _make_processor(frame_interval=10)
        output = tmp_path / "output.avi"

        embed_result = wm.embed(sample_avi, sample_payload, output)
        assert embed_result.success, f"Embed failed: {embed_result.message}"

        extract_result = wm.extract(output)
        assert extract_result.success, f"Extract failed: {extract_result.message}"
        assert extract_result.payload is not None
        assert extract_result.payload.employee_id == "E001"


# ========== 质量指标测试 ==========


@pytest.mark.slow
class TestQualityMetrics:
    """验证嵌入结果中的视频质量指标。"""

    def test_embed_result_has_watermarked_frames(self, sample_avi, sample_payload, tmp_path):
        """EmbedResult.quality_metrics 应包含 watermarked_frames 键。"""
        wm = _make_processor(frame_interval=10)
        output = tmp_path / "output.avi"
        result = wm.embed(sample_avi, sample_payload, output)

        assert result.success
        assert "watermarked_frames" in result.quality_metrics
        # 20 帧、interval=10 → 帧 0 和帧 10 被嵌入 = 2 帧
        assert result.quality_metrics["watermarked_frames"] >= 1


# ========== 输出视频可读测试 ==========


@pytest.mark.slow
class TestOutputReadable:
    """输出视频文件应可被 OpenCV 正常读取。"""

    def test_output_openable_with_videocapture(self, sample_avi, sample_payload, tmp_path):
        """输出 AVI 可用 cv2.VideoCapture 打开并读取帧。"""
        wm = _make_processor(frame_interval=10)
        output = tmp_path / "output.avi"
        wm.embed(sample_avi, sample_payload, output)

        cap = cv2.VideoCapture(str(output))
        assert cap.isOpened(), "Output video should be openable"

        ret, frame = cap.read()
        assert ret, "Should be able to read at least one frame"
        assert frame is not None
        cap.release()


# ========== 参数校验测试 ==========


class TestParameterValidation:
    """构造参数校验。"""

    def test_frame_interval_zero_raises(self):
        """frame_interval=0 应抛出 ValueError。"""
        with pytest.raises(ValueError, match="positive"):
            VideoWatermark(
                strength=WatermarkStrength.MEDIUM,
                frame_interval=0,
            )


# ========== 支持扩展名测试 ==========


class TestSupportedExtensions:
    """验证 supported_extensions 返回正确的格式列表。"""

    def test_supported_extensions(self):
        """应包含 .mp4 / .avi / .mkv / .mov 四种格式。"""
        wm = _make_processor()
        exts = wm.supported_extensions()
        assert exts == [".mp4", ".avi", ".mkv", ".mov"]


# ========== 边界情况测试 ==========


@pytest.mark.slow
class TestEdgeCases:
    """小尺寸视频等边界场景。"""

    def test_tiny_video_fails(self, sample_payload, tmp_path):
        """
        帧尺寸低于 256x256 的视频，embed 应失败（不崩溃）。
        _MIN_FRAME_SIZE = 256，此处用 64x64 触发。
        """
        wm = _make_processor(frame_interval=5)
        tiny_avi = tmp_path / "tiny.avi"
        _create_tiny_avi(tiny_avi, width=64, height=64, n_frames=10)
        output = tmp_path / "output.avi"

        result = wm.embed(tiny_avi, sample_payload, output)
        assert not result.success
        # 错误信息应提到尺寸过小
        assert "small" in result.message.lower() or "size" in result.message.lower()
