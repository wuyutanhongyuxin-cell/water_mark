"""
音频盲水印处理器测试（DWT-DCT-QIM）。

测试 AudioWatermark 的嵌入/提取往返、SNR 质量指标、
短音频拒绝、支持格式列表、有损格式拒绝。
"""

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from src.watermarks.base import WatermarkStrength
from src.watermarks.audio_wm import AudioWatermark


# ========== 辅助函数 ==========


def _make_processor():
    """创建音频水印处理器。"""
    return AudioWatermark(strength=WatermarkStrength.MEDIUM)


def _create_short_wav(path: Path, n_samples: int = 100):
    """生成极短的 WAV 文件（低于 _MIN_SAMPLES 阈值）。"""
    signal = np.zeros(n_samples)
    sf.write(str(path), signal, 44100, format="WAV", subtype="PCM_16")


# ========== 嵌入→提取往返测试 ==========


class TestAudioRoundtrip:
    """嵌入后提取，验证水印载荷一致性。"""

    def test_wav_roundtrip(self, sample_wav, sample_payload, tmp_path):
        """WAV 文件嵌入→提取，employee_id 应一致。"""
        wm = _make_processor()
        output = tmp_path / "output.wav"

        embed_result = wm.embed(sample_wav, sample_payload, output)
        assert embed_result.success, f"Embed failed: {embed_result.message}"

        extract_result = wm.extract(output)
        assert extract_result.success, f"Extract failed: {extract_result.message}"
        assert extract_result.payload is not None
        assert extract_result.payload.employee_id == "E001"


# ========== 质量指标测试 ==========


class TestQualityMetrics:
    """验证嵌入结果中的音频质量指标。"""

    def test_embed_result_has_snr(self, sample_wav, sample_payload, tmp_path):
        """EmbedResult.quality_metrics 应包含 snr 键。"""
        wm = _make_processor()
        output = tmp_path / "output.wav"
        result = wm.embed(sample_wav, sample_payload, output)

        assert result.success
        assert "snr" in result.quality_metrics

    def test_snr_is_positive(self, sample_wav, sample_payload, tmp_path):
        """SNR 应为正值（水印不应严重损坏音频）。"""
        wm = _make_processor()
        output = tmp_path / "output.wav"
        result = wm.embed(sample_wav, sample_payload, output)

        assert result.success
        assert result.quality_metrics["snr"] > 0


# ========== 短音频拒绝测试 ==========


class TestShortAudio:
    """音频采样点不足时应拒绝嵌入。"""

    def test_audio_too_short_fails(self, sample_payload, tmp_path):
        """采样点数 < _MIN_SAMPLES (65536) 时，embed 应失败。"""
        wm = _make_processor()
        short_wav = tmp_path / "short.wav"
        _create_short_wav(short_wav, n_samples=100)
        output = tmp_path / "output.wav"

        result = wm.embed(short_wav, sample_payload, output)
        assert not result.success
        # 错误信息应提到 "short" 或 "samples"
        assert "short" in result.message.lower() or "sample" in result.message.lower()


# ========== 支持扩展名与文件校验测试 ==========


class TestSupportedExtensions:
    """验证格式支持和有损格式拒绝。"""

    def test_supported_extensions(self):
        """应包含 .wav 和 .flac（仅无损格式）。"""
        wm = _make_processor()
        exts = wm.supported_extensions()
        assert exts == [".wav", ".flac"]

    def test_validate_file_rejects_mp3(self, tmp_path):
        """validate_file 应拒绝 .mp3 扩展名（有损格式）。"""
        wm = _make_processor()
        # 创建一个假的 mp3 文件（内容无关紧要，只测扩展名过滤）
        fake_mp3 = tmp_path / "test.mp3"
        fake_mp3.write_bytes(b"\x00" * 100)

        assert not wm.validate_file(fake_mp3)
