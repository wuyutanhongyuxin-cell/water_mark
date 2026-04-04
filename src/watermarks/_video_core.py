"""
视频帧处理 + ffmpeg 工具函数。

为 video_wm.py 提供帧级别水印嵌入/提取，复用 blind-watermark DWT-DCT-SVD。
ffmpeg 用于保留音轨（可选系统工具）。
"""

import shutil
import subprocess
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from loguru import logger

import blind_watermark
blind_watermark.bw_notes.close()
from blind_watermark import WaterMark

from src.watermarks.base import WatermarkStrength
from src.watermarks._bwm_constants import PASSWORD_WM, PASSWORD_IMG, STRENGTH_MAP
from src.watermarks.payload_codec import PAYLOAD_BITS

# 最小帧尺寸（blind-watermark 内部 DCT 分块要求）
_MIN_FRAME_SIZE = 256


def get_video_props(path: Path) -> Optional[dict]:
    """获取视频属性：fps, width, height, frame_count。"""
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        cap.release()
        logger.warning(f"Cannot open video: {path}")
        return None
    props = {
        "fps": cap.get(cv2.CAP_PROP_FPS),
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "frame_count": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
    }
    cap.release()
    return props


def has_ffmpeg() -> bool:
    """检查系统是否安装了 ffmpeg。"""
    return shutil.which("ffmpeg") is not None


def extract_audio_track(video_path: Path, audio_out: Path) -> bool:
    """用 ffmpeg 提取视频音轨（无转码复制）。"""
    if not has_ffmpeg():
        return False
    try:
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", str(video_path),
             "-vn", "-acodec", "copy", str(audio_out)],
            capture_output=True, timeout=120,
        )
        return result.returncode == 0 and audio_out.exists()
    except Exception as e:
        logger.warning(f"ffmpeg extract audio failed: {e}")
        return False


def mux_video_audio(video_path: Path, audio_path: Path, output: Path) -> bool:
    """用 ffmpeg 合并视频流和音轨。"""
    if not has_ffmpeg():
        return False
    try:
        result = subprocess.run(
            ["ffmpeg", "-y",
             "-i", str(video_path), "-i", str(audio_path),
             "-c:v", "copy", "-c:a", "copy", "-shortest",
             str(output)],
            capture_output=True, timeout=300,
        )
        return result.returncode == 0 and output.exists()
    except Exception as e:
        logger.warning(f"ffmpeg mux failed: {e}")
        return False


def embed_frame(
    img_bgr: np.ndarray, bits: list[int], strength: WatermarkStrength,
) -> Optional[np.ndarray]:
    """在单帧图像中嵌入水印（复用 blind-watermark DWT-DCT-SVD）。"""
    h, w = img_bgr.shape[:2]
    if h < _MIN_FRAME_SIZE or w < _MIN_FRAME_SIZE:
        return None
    try:
        bwm = WaterMark(password_wm=PASSWORD_WM, password_img=PASSWORD_IMG)
        d1, d2 = STRENGTH_MAP[strength]
        bwm.bwm_core.d1 = d1
        bwm.bwm_core.d2 = d2
        bwm.bwm_core.read_img_arr(img_bgr)
        bwm.read_wm(bits, mode='bit')
        return bwm.embed()
    except Exception as e:
        logger.warning(f"embed_frame failed: {e}")
        return None


def extract_frame(
    img_bgr: np.ndarray, strength: WatermarkStrength,
) -> Optional[list[int]]:
    """从单帧图像中提取水印比特。"""
    h, w = img_bgr.shape[:2]
    if h < _MIN_FRAME_SIZE or w < _MIN_FRAME_SIZE:
        return None
    try:
        bwm = WaterMark(password_wm=PASSWORD_WM, password_img=PASSWORD_IMG)
        d1, d2 = STRENGTH_MAP[strength]
        bwm.bwm_core.d1 = d1
        bwm.bwm_core.d2 = d2
        raw = bwm.extract(
            embed_img=img_bgr, wm_shape=PAYLOAD_BITS, mode='bit',
        )
        return (np.array(raw) > 0.5).astype(int).tolist()
    except Exception as e:
        logger.warning(f"extract_frame failed: {e}")
        return None
