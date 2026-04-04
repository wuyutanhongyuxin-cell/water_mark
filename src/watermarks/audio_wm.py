"""
音频盲水印处理器（DWT-DCT-QIM）。

支持 WAV/FLAC 无损格式。有损格式（MP3/OGG）不支持（重编码破坏水印）。
使用 soundfile 读写音频，嵌入在左声道的 DWT detail 系数 DCT 域。
载荷编解码复用 payload_codec.py（v2 加密 1024-bit）。
"""

import io
from pathlib import Path
from typing import Optional

import numpy as np
from loguru import logger

from src.watermarks.base import (
    WatermarkBase, WatermarkStrength,
    WatermarkPayload, EmbedResult, ExtractResult,
)
from src.watermarks.payload_codec import payload_to_bits, bits_to_payload
from src.watermarks._audio_core import (
    embed_audio_signal, extract_audio_signal, calc_snr, DELTA_MAP,
)


# 有损格式不支持（有损重编码破坏水印）
_UNSUPPORTED_LOSSY = {".mp3", ".ogg"}

# 最低采样点：1024 bits × 32 block_size × 2 (DWT) = 65536
_MIN_SAMPLES = 65536


class AudioWatermark(WatermarkBase):
    """音频盲水印处理器。DWT-DCT-QIM 频域嵌入，支持 WAV/FLAC。"""

    def embed(
        self, input_path: Path, payload: WatermarkPayload,
        output_path: Path,
    ) -> EmbedResult:
        """将水印嵌入音频文件（v2 加密格式）。"""
        # 编码载荷为 1024 bits
        try:
            bits = payload_to_bits(payload)
        except ValueError as e:
            return EmbedResult(success=False, message=str(e))

        # 读取音频
        signal, sr = _read_audio(input_path)
        if signal is None:
            return EmbedResult(success=False, message=f"Cannot read audio: {input_path}")

        # 采样点数量检查
        n_samples = signal.shape[0]
        if n_samples < _MIN_SAMPLES:
            return EmbedResult(
                success=False,
                message=f"Audio too short: {n_samples} < {_MIN_SAMPLES} samples",
            )

        # 分离声道：立体声取左声道嵌入，其余声道原样保留
        stereo = signal.ndim > 1 and signal.shape[1] >= 2
        left = signal[:, 0].copy() if stereo else signal.copy()
        original_left = left.copy()

        # 嵌入水印
        delta = DELTA_MAP[self.strength.value]
        watermarked_left = embed_audio_signal(left, bits, delta)

        # 计算 SNR（嵌入质量指标）
        snr = calc_snr(original_left, watermarked_left)

        # 组装输出信号
        if stereo:
            out_signal = signal.copy()
            out_signal[:, 0] = watermarked_left
        else:
            out_signal = watermarked_left

        # 写入输出文件
        if not _write_audio(output_path, out_signal, sr):
            return EmbedResult(success=False, message=f"Failed to write: {output_path}")

        logger.info(
            f"Audio watermark embedded: {input_path.name} "
            f"(delta={delta}, SNR={snr:.1f}dB)"
        )
        return EmbedResult(
            success=True, output_path=output_path,
            message=f"Embedded audio watermark (SNR={snr:.1f}dB)",
            quality_metrics={"snr": round(snr, 2)},
        )

    def extract(self, file_path: Path) -> ExtractResult:
        """从音频文件中提取水印。"""
        signal, sr = _read_audio(file_path)
        if signal is None:
            return ExtractResult(
                success=False, confidence=0.0,
                message=f"Cannot read audio: {file_path}",
            )

        # 立体声取左声道
        channel = signal[:, 0] if (signal.ndim > 1 and signal.shape[1] >= 2) else signal

        # 提取 bits 并解码
        delta = DELTA_MAP[self.strength.value]
        bits = extract_audio_signal(channel, delta)
        payload = bits_to_payload(bits)

        if payload is None:
            return ExtractResult(
                success=False, confidence=0.0,
                message="Failed to decode watermark from audio",
            )

        logger.info(f"Extracted audio watermark from {file_path.name}")
        return ExtractResult(
            success=True, payload=payload, confidence=1.0,
            message=f"Employee: {payload.employee_id}",
        )

    def supported_extensions(self) -> list[str]:
        """支持的音频格式（仅无损：WAV PCM / FLAC 无损压缩）。"""
        return [".wav", ".flac"]

    def validate_file(self, file_path: Path) -> bool:
        """预检查：排除 MP3 等有损格式。"""
        if file_path.suffix.lower() in _UNSUPPORTED_LOSSY:
            logger.warning(
                f"{file_path.suffix.upper()} not supported "
                f"(lossy format destroys watermark): {file_path.name}"
            )
            return False
        return super().validate_file(file_path)


# ==================== 内部工具函数 ====================


def _read_audio(path: Path) -> tuple[Optional[np.ndarray], int]:
    """读取音频文件 → (signal float64, sample_rate)。中文路径 BytesIO fallback。"""
    try:
        import soundfile as sf
    except ImportError:
        logger.error("soundfile not installed: pip install soundfile")
        return None, 0

    # 优先直接路径读取
    try:
        signal, sr = sf.read(str(path))
        return signal.astype(np.float64), sr
    except Exception:
        logger.debug(f"Direct path read failed for {path}, trying BytesIO fallback")

    # Fallback: BytesIO（中文路径兼容）
    try:
        data = Path(path).read_bytes()
        signal, sr = sf.read(io.BytesIO(data))
        return signal.astype(np.float64), sr
    except Exception as e:
        logger.warning(f"Failed to read audio {path}: {e}")
        return None, 0


def _write_audio(path: Path, signal: np.ndarray, sr: int) -> bool:
    """写入音频文件。根据扩展名选择格式和子类型。"""
    try:
        import soundfile as sf
    except ImportError:
        logger.error("soundfile not installed")
        return False

    ext = Path(path).suffix.lower()
    # 格式 + 子类型映射
    fmt_map = {".wav": ("WAV", "PCM_16"), ".flac": ("FLAC", "PCM_16")}
    fmt, subtype = fmt_map.get(ext, ("WAV", "PCM_16"))

    try:
        sf.write(str(path), signal, sr, format=fmt, subtype=subtype)
        return True
    except Exception:
        logger.debug(f"Direct path write failed for {path}, trying BytesIO fallback")

    # Fallback: BytesIO + write_bytes（中文路径）
    try:
        buf = io.BytesIO()
        sf.write(buf, signal, sr, format=fmt, subtype=subtype)
        Path(path).write_bytes(buf.getvalue())
        return True
    except Exception as e:
        logger.warning(f"Failed to write audio {path}: {e}")
        return False
