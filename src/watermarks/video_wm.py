"""视频盲水印处理器（逐帧 DWT-DCT-SVD + 多数表决提取）。"""

import shutil
import tempfile
from pathlib import Path

import cv2
import numpy as np
from loguru import logger

from src.watermarks.base import (
    WatermarkBase, WatermarkStrength,
    WatermarkPayload, EmbedResult, ExtractResult,
)
from src.watermarks.payload_codec import (
    payload_to_bits, bits_to_payload, PAYLOAD_BITS,
)
from src.watermarks._video_core import (
    get_video_props, has_ffmpeg,
    extract_audio_track, mux_video_audio,
    embed_frame, extract_frame, _MIN_FRAME_SIZE,
)

_DEFAULT_FRAME_INTERVAL = 10


class VideoWatermark(WatermarkBase):
    """视频盲水印处理器。逐帧 DWT-DCT-SVD 嵌入 + 多数表决提取。"""

    def __init__(self, strength: WatermarkStrength = WatermarkStrength.MEDIUM,
                 frame_interval: int = _DEFAULT_FRAME_INTERVAL):
        super().__init__(strength)
        if frame_interval <= 0:
            raise ValueError(f"frame_interval must be positive, got {frame_interval}")
        self.frame_interval = frame_interval

    def embed(self, input_path: Path, payload: WatermarkPayload,
              output_path: Path) -> EmbedResult:
        """将水印嵌入视频（每 N 帧嵌入一次）。"""
        try:
            bits = payload_to_bits(payload)
        except ValueError as e:
            return EmbedResult(success=False, message=str(e))

        props = get_video_props(input_path)
        if props is None:
            return EmbedResult(success=False, message=f"Cannot open video: {input_path}")
        err = _validate_video(props, self.frame_interval)
        if err:
            return EmbedResult(success=False, message=err)

        tmp_dir = Path(tempfile.mkdtemp(prefix="wm_video_"))
        tmp_avi = tmp_dir / "watermarked.avi"

        fps = props["fps"]
        if not fps or fps <= 0:
            logger.warning(f"FPS undetectable for {input_path.name}, defaulting to 30.0")
            fps = 30.0
        w, h = props["width"], props["height"]
        # FFV1 无损编码作为中间格式，保护水印不被有损压缩破坏
        fourcc = cv2.VideoWriter_fourcc(*"FFV1")

        cap = cv2.VideoCapture(str(input_path))
        writer = cv2.VideoWriter(str(tmp_avi), fourcc, fps, (w, h))
        if not writer.isOpened():
            cap.release()
            shutil.rmtree(str(tmp_dir), ignore_errors=True)
            return EmbedResult(success=False, message=f"Cannot create video writer")
        wm_count, total = 0, 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                # 每 frame_interval 帧嵌入水印
                if total % self.frame_interval == 0:
                    wm_frame = embed_frame(frame, bits, self.strength)
                    if wm_frame is not None:
                        frame = np.clip(wm_frame, 0, 255).astype(np.uint8)
                        wm_count += 1
                writer.write(frame)
                total += 1
                if total % 100 == 0:
                    logger.debug(f"Video embed: {total}/{props['frame_count']} frames")
        finally:
            cap.release()
            writer.release()

        if wm_count == 0:
            shutil.rmtree(str(tmp_dir), ignore_errors=True)
            return EmbedResult(success=False, message="No frames were watermarked")
        if not _finalize_output(input_path, tmp_avi, output_path, tmp_dir):
            return EmbedResult(success=False, message="Failed to produce output video")

        msg = f"Embedded {wm_count}/{total} frames"
        logger.info(f"Video watermark: {input_path.name} ({msg})")
        return EmbedResult(
            success=True, output_path=output_path, message=msg,
            quality_metrics={"watermarked_frames": wm_count, "total_frames": total})

    def extract(self, file_path: Path) -> ExtractResult:
        """从视频中提取水印（多数表决）。"""
        if not file_path.exists():
            return ExtractResult(
                success=False, confidence=0.0, message=f"File not found: {file_path}")
        cap = cv2.VideoCapture(str(file_path))
        if not cap.isOpened():
            return ExtractResult(
                success=False, confidence=0.0,
                message=f"Cannot open video: {file_path}",
            )

        bit_arrays = []
        frame_idx = 0
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                if frame_idx % self.frame_interval == 0:
                    bits = extract_frame(frame, self.strength)
                    if bits is not None:
                        bit_arrays.append(bits)
                frame_idx += 1
        finally:
            cap.release()

        if not bit_arrays:
            return ExtractResult(
                success=False, confidence=0.0,
                message="No watermark frames extracted",
            )

        # 多数表决 + 解码
        voted_bits, confidence = _majority_vote(bit_arrays)
        payload = bits_to_payload(voted_bits)

        if payload is None:
            return ExtractResult(
                success=False, confidence=confidence,
                message=f"Decode failed ({len(bit_arrays)} frames voted)",
            )

        logger.info(
            f"Extracted video watermark: {file_path.name} "
            f"({len(bit_arrays)} frames, conf={confidence:.2f})"
        )
        return ExtractResult(
            success=True, payload=payload, confidence=confidence,
            message=f"Employee: {payload.employee_id} ({len(bit_arrays)} frames)",
        )

    def supported_extensions(self) -> list[str]:
        return [".mp4", ".avi", ".mkv", ".mov"]


def _validate_video(props: dict, frame_interval: int) -> str:
    if props["frame_count"] < frame_interval:
        return f"Too few frames: {props['frame_count']} < {frame_interval}"
    if props["width"] < _MIN_FRAME_SIZE or props["height"] < _MIN_FRAME_SIZE:
        return f"Frame too small: {props['width']}x{props['height']} < {_MIN_FRAME_SIZE}"
    return ""


def _majority_vote(bit_arrays: list[list[int]]) -> tuple[list[int], float]:
    """多数表决：对每个 bit 位置取多数值。返回 (voted_bits, 最低位置信度)。"""
    n = len(bit_arrays)
    voted = []
    min_conf = 1.0
    for pos in range(PAYLOAD_BITS):
        ones = sum(ba[pos] for ba in bit_arrays if pos < len(ba))
        ratio = ones / n
        voted.append(1 if ratio >= 0.5 else 0)
        min_conf = min(min_conf, max(ratio, 1.0 - ratio))
    return voted, min_conf


def _finalize_output(input_path: Path, tmp_avi: Path,
                     output_path: Path, tmp_dir: Path) -> bool:
    """合并音轨 → 输出最终文件。ffmpeg 不可用则直接复制（无音轨）。"""
    try:
        if has_ffmpeg():
            audio_tmp = tmp_dir / "audio.aac"
            if extract_audio_track(input_path, audio_tmp):
                return mux_video_audio(tmp_avi, audio_tmp, output_path)
            logger.info("No audio track detected, video-only output")
        # 无 ffmpeg 时：仅允许 .avi 输出（避免 AVI 容器伪装为 MP4/MKV）
        if not has_ffmpeg() and output_path.suffix.lower() != ".avi":
            logger.error(f"ffmpeg required to produce {output_path.suffix} output")
            return False
        shutil.copy2(str(tmp_avi), str(output_path))
        if not has_ffmpeg():
            logger.warning("ffmpeg unavailable — output is AVI container without audio")
        return output_path.exists()
    except Exception as e:
        logger.warning(f"Finalize output failed: {e}")
        return False
    finally:
        shutil.rmtree(str(tmp_dir), ignore_errors=True)
