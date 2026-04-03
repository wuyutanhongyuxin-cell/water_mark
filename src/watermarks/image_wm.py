"""
图像盲水印处理器（DWT-DCT-SVD）。

使用 blind-watermark 库实现频域盲水印嵌入与提取。
载荷采用固定 512-bit 编码，提取时无需存储 wm_size。
"""

import json
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

# 固定载荷编码长度：64 字节 = 512 bits
# 足够存储 employee_id + timestamp + file_hash 的压缩 JSON
_PAYLOAD_BYTES = 64
_PAYLOAD_BITS = _PAYLOAD_BYTES * 8

# 嵌入强度映射：(d1, d2) — d1/d2 越大越鲁棒但 PSNR 越低
_STRENGTH_MAP = {
    WatermarkStrength.LOW: (15, 8),       # PSNR ~47dB，低鲁棒性
    WatermarkStrength.MEDIUM: (36, 20),   # PSNR ~38dB，平衡（默认）
    WatermarkStrength.HIGH: (64, 36),     # PSNR ~33dB，高鲁棒性
}

# 固定密码种子（后续可由 security 模块管理）
_PASSWORD_WM = 20260403
_PASSWORD_IMG = 20260403


class ImageWatermark(WatermarkBase):
    """图像盲水印处理器。DWT-DCT-SVD 频域嵌入，支持 JPG/PNG/BMP/WebP。"""

    def embed(self, input_path: Path, payload: WatermarkPayload,
              output_path: Path) -> EmbedResult:
        """将水印嵌入图像文件。"""
        # 1. 序列化载荷为固定长度 bit 数组
        try:
            bits = _payload_to_bits(payload)
        except ValueError as e:
            return EmbedResult(success=False, message=str(e))

        # 2. 配置 blind-watermark 引擎
        bwm = WaterMark(password_wm=_PASSWORD_WM, password_img=_PASSWORD_IMG)
        d1, d2 = _STRENGTH_MAP[self.strength]
        bwm.bwm_core.d1 = d1
        bwm.bwm_core.d2 = d2

        # 3. 读取原图 + 嵌入水印
        bwm.read_img(filename=str(input_path))
        bwm.read_wm(bits, mode='bit')
        embed_img = bwm.embed(filename=str(output_path))

        # 4. 计算质量指标（PSNR）
        metrics = _calc_quality(str(input_path), embed_img)

        logger.info(
            f"Image watermark embedded: {input_path.name} "
            f"(d1={d1}, PSNR={metrics.get('psnr', 'N/A')}dB)"
        )
        return EmbedResult(
            success=True, output_path=output_path,
            message=f"Embedded (PSNR={metrics.get('psnr', 'N/A')}dB)",
            quality_metrics=metrics,
        )

    def extract(self, file_path: Path) -> ExtractResult:
        """从图像文件中提取水印。"""
        # 1. 配置引擎（密码和强度必须与嵌入时一致）
        bwm = WaterMark(password_wm=_PASSWORD_WM, password_img=_PASSWORD_IMG)
        d1, d2 = _STRENGTH_MAP[self.strength]
        bwm.bwm_core.d1 = d1
        bwm.bwm_core.d2 = d2

        # 2. 提取 bit 数组
        raw = bwm.extract(
            filename=str(file_path),
            wm_shape=_PAYLOAD_BITS,
            mode='bit',
        )
        bits = (np.array(raw) > 0.5).astype(int).tolist()

        # 3. 反序列化为 WatermarkPayload
        payload = _bits_to_payload(bits)
        if payload is None:
            return ExtractResult(
                success=False, confidence=0.0,
                message="Failed to decode watermark from image",
            )

        logger.info(f"Extracted watermark from {file_path.name}: {payload.employee_id}")
        return ExtractResult(
            success=True, payload=payload, confidence=1.0,
            message=f"Employee: {payload.employee_id}",
        )

    def supported_extensions(self) -> list[str]:
        """支持的图像格式（OpenCV 可读写的常见格式）。"""
        return [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"]


# ==================== 内部工具函数 ====================


def _payload_to_bits(payload: WatermarkPayload) -> list[int]:
    """将 WatermarkPayload 序列化为固定 512-bit 数组。"""
    # 压缩 JSON：用短键名减少空间占用
    data = {
        "e": payload.employee_id,
        "t": payload.timestamp,
        "h": payload.file_hash,
    }
    json_bytes = json.dumps(data, separators=(",", ":")).encode("utf-8")

    if len(json_bytes) > _PAYLOAD_BYTES:
        raise ValueError(
            f"Payload too large: {len(json_bytes)} bytes > {_PAYLOAD_BYTES} limit. "
            f"Shorten employee_id or custom_data."
        )

    # 用 0x00 填充到固定长度
    padded = json_bytes.ljust(_PAYLOAD_BYTES, b"\x00")

    # 每字节展开为 8 bits（大端序）
    bits = []
    for byte_val in padded:
        for i in range(7, -1, -1):
            bits.append((byte_val >> i) & 1)
    return bits


def _bits_to_payload(bits: list[int]) -> Optional[WatermarkPayload]:
    """将 512-bit 数组反序列化为 WatermarkPayload。失败返回 None。"""
    # bits → bytes
    raw_bytes = bytearray()
    for i in range(0, len(bits), 8):
        byte_val = 0
        for j in range(8):
            if i + j < len(bits):
                byte_val = (byte_val << 1) | bits[i + j]
        raw_bytes.append(byte_val)

    # 去掉 0x00 填充，尝试 JSON 解析
    json_bytes = bytes(raw_bytes).rstrip(b"\x00")
    try:
        data = json.loads(json_bytes.decode("utf-8"))
        return WatermarkPayload(
            employee_id=data.get("e", ""),
            timestamp=data.get("t", ""),
            file_hash=data.get("h", ""),
        )
    except (json.JSONDecodeError, UnicodeDecodeError, KeyError):
        return None


def _calc_quality(original_path: str, embed_img: np.ndarray) -> dict:
    """计算原图与水印图之间的 PSNR。"""
    try:
        original = cv2.imread(original_path)
        if original is None:
            return {}
        watermarked = np.clip(embed_img, 0, 255).astype(np.uint8)
        # 确保尺寸一致
        if original.shape != watermarked.shape:
            return {}
        psnr = cv2.PSNR(original, watermarked)
        return {"psnr": round(float(psnr), 2)}
    except Exception as e:
        logger.warning(f"Quality calculation failed: {e}")
        return {}
