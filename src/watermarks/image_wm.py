"""
图像盲水印处理器（DWT-DCT-SVD）。

使用 blind-watermark 库实现频域盲水印嵌入与提取。
v2 格式：1024-bit 载荷，AES-256-GCM 加密。
v1 兼容：512-bit 明文 JSON（Phase 2 遗留，回退解码）。
载荷编解码逻辑见 payload_codec.py。
"""

from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from loguru import logger

# 关闭 blind-watermark 的欢迎消息（必须在 import WaterMark 之前）
import blind_watermark
blind_watermark.bw_notes.close()
from blind_watermark import WaterMark

from src.watermarks.base import (
    WatermarkBase, WatermarkStrength,
    WatermarkPayload, EmbedResult, ExtractResult,
)
from src.watermarks.payload_codec import (
    payload_to_bits, bits_to_payload, decode_v1_json,
    bits_to_bytes, PAYLOAD_BITS, _LEGACY_PAYLOAD_BITS,
)
from src.watermarks._bwm_constants import PASSWORD_WM, PASSWORD_IMG, STRENGTH_MAP


class ImageWatermark(WatermarkBase):
    """图像盲水印处理器。DWT-DCT-SVD 频域嵌入，支持 JPG/PNG/BMP/WebP。"""

    def embed(self, input_path: Path, payload: WatermarkPayload,
              output_path: Path) -> EmbedResult:
        """将水印嵌入图像文件（v2 加密格式）。"""
        try:
            bits = payload_to_bits(payload)
        except ValueError as e:
            return EmbedResult(success=False, message=str(e))

        # 配置 blind-watermark 引擎
        bwm = WaterMark(password_wm=PASSWORD_WM, password_img=PASSWORD_IMG)
        d1, d2 = STRENGTH_MAP[self.strength]
        bwm.bwm_core.d1 = d1
        bwm.bwm_core.d2 = d2

        # 读取原图（用 imdecode 支持中文路径）+ 嵌入水印
        img = _imread_safe(input_path)
        if img is None:
            return EmbedResult(success=False, message=f"Cannot read image: {input_path}")
        bwm.bwm_core.read_img_arr(img)
        bwm.read_wm(bits, mode='bit')
        # embed() 不传 filename，手动写入以支持中文输出路径
        embed_img = bwm.embed()
        if not _imwrite_safe(output_path, embed_img):
            return EmbedResult(success=False, message=f"Failed to write image: {output_path}")

        metrics = _calc_quality(img, embed_img)
        logger.info(
            f"Image watermark embedded (v2): {input_path.name} "
            f"(d1={d1}, PSNR={metrics.get('psnr', 'N/A')}dB)"
        )
        return EmbedResult(
            success=True, output_path=output_path,
            message=f"Embedded v2 (PSNR={metrics.get('psnr', 'N/A')}dB)",
            quality_metrics=metrics,
        )

    def extract(self, file_path: Path) -> ExtractResult:
        """从图像文件中提取水印（自动识别 v1/v2 格式）。"""
        bwm = WaterMark(password_wm=PASSWORD_WM, password_img=PASSWORD_IMG)
        d1, d2 = STRENGTH_MAP[self.strength]
        bwm.bwm_core.d1 = d1
        bwm.bwm_core.d2 = d2

        # 读取图像（imdecode 支持中文路径）
        img = _imread_safe(file_path)
        if img is None:
            return ExtractResult(
                success=False, confidence=0.0,
                message=f"Cannot read image: {file_path}",
            )

        # 先尝试 v2 (1024 bits)，用 embed_img 参数避免内部 cv2.imread
        raw = bwm.extract(
            embed_img=img, wm_shape=PAYLOAD_BITS, mode='bit',
        )
        bits = (np.array(raw) > 0.5).astype(int).tolist()
        payload = bits_to_payload(bits)

        # v2 失败则回退 v1 (512 bits)
        if payload is None:
            payload = _decode_legacy(img, bwm)

        if payload is None:
            return ExtractResult(
                success=False, confidence=0.0,
                message="Failed to decode watermark from image",
            )

        eid = payload.employee_id
        masked_id = eid[:2] + "***" + eid[-1:] if len(eid) > 3 else "***"
        logger.info(f"Extracted watermark from {file_path.name}: {masked_id}")
        return ExtractResult(
            success=True, payload=payload, confidence=1.0,
            message=f"Employee: {payload.employee_id}",
        )

    def supported_extensions(self) -> list[str]:
        """支持的图像格式（OpenCV 可读写的常见格式）。"""
        return [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"]


# ==================== 内部工具函数 ====================


def _imread_safe(path: Path) -> Optional[np.ndarray]:
    """读取图像，用 imdecode 支持中文路径（cv2.imread 不支持）。"""
    try:
        buf = np.frombuffer(Path(path).read_bytes(), dtype=np.uint8)
        return cv2.imdecode(buf, cv2.IMREAD_COLOR)
    except Exception as e:
        logger.warning(f"Failed to read image {path}: {e}")
        return None


def _imwrite_safe(path: Path, img: np.ndarray) -> bool:
    """写入图像，用 imencode 支持中文路径（cv2.imwrite 不支持）。"""
    ext = Path(path).suffix or ".png"
    success, buf = cv2.imencode(ext, img)
    if success:
        Path(path).write_bytes(buf.tobytes())
    return success


def _decode_legacy(img: np.ndarray, bwm: WaterMark) -> Optional[WatermarkPayload]:
    """回退尝试 v1 (512 bits) 提取。Phase 2 旧水印兼容。"""
    try:
        raw = bwm.extract(
            embed_img=img, wm_shape=_LEGACY_PAYLOAD_BITS, mode='bit',
        )
        bits = (np.array(raw) > 0.5).astype(int).tolist()
        return decode_v1_json(bits_to_bytes(bits))
    except Exception:
        return None


def _calc_quality(original: np.ndarray, embed_img: np.ndarray) -> dict:
    """计算原图与水印图之间的 PSNR。"""
    try:
        watermarked = np.clip(embed_img, 0, 255).astype(np.uint8)
        if original.shape != watermarked.shape:
            return {}
        psnr = cv2.PSNR(original, watermarked)
        return {"psnr": round(float(psnr), 2)}
    except Exception as e:
        logger.warning(f"Quality calculation failed: {e}")
        return {}
