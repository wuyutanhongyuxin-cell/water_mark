"""
PDF 盲水印处理器（渲染→图像水印→重建）。

输出 PDF 为纯图像，丢失文本可选性（最大化水印鲁棒性）。
嵌入前添加微弱噪声（sigma=3）为 DWT-DCT-SVD 提供频域纹理。
"""

from pathlib import Path
from typing import Optional

import cv2
import fitz  # PyMuPDF
import numpy as np
from loguru import logger

import blind_watermark
blind_watermark.bw_notes.close()
from blind_watermark import WaterMark

from src.watermarks.base import (
    WatermarkBase, WatermarkStrength,
    WatermarkPayload, EmbedResult, ExtractResult,
)
from src.watermarks.payload_codec import (
    payload_to_bits, bits_to_payload, _PAYLOAD_BITS,
)

# 复用 image_wm 的参数保持一致
_PASSWORD_WM = 20260403
_PASSWORD_IMG = 20260403
_STRENGTH_MAP = {
    WatermarkStrength.LOW: (15, 8),
    WatermarkStrength.MEDIUM: (36, 20),
    WatermarkStrength.HIGH: (64, 36),
}

# PDF 渲染分辨率（嵌入和提取必须一致）
_DEFAULT_DPI = 200

# 噪声强度：为纯色区域添加频域纹理（sigma=3，PSNR≈40dB，肉眼不可见）
_NOISE_SIGMA = 3
# 固定随机种子确保嵌入/提取的噪声一致
_NOISE_SEED = 20260403


class PdfWatermark(WatermarkBase):
    """PDF 盲水印处理器。渲染→噪声预处理→DWT-DCT-SVD→重建。"""

    def embed(
        self, input_path: Path, payload: WatermarkPayload,
        output_path: Path,
    ) -> EmbedResult:
        """将水印嵌入 PDF（渲染第一页为图像后嵌入 DWT-DCT-SVD）。"""
        try:
            bits = payload_to_bits(payload)
        except ValueError as e:
            return EmbedResult(success=False, message=str(e))

        doc = None
        new_doc = None
        try:
            doc = fitz.open(str(input_path))
            if doc.page_count == 0:
                return EmbedResult(success=False, message="PDF has no pages")

            scale = _DEFAULT_DPI / 72
            mat = fitz.Matrix(scale, scale)
            new_doc = fitz.open()  # 空白 PDF

            for page_idx in range(doc.page_count):
                page = doc[page_idx]
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img = _pixmap_to_bgr(pix)

                # 仅第一页：添加噪声 + 嵌入水印
                if page_idx == 0:
                    img = _add_texture_noise(img)
                    img = _embed_to_image(img, bits, self.strength)

                _insert_image_page(new_doc, img, page.rect)

            new_doc.save(str(output_path))
            logger.info(
                f"PDF watermark embedded: {input_path.name} "
                f"({doc.page_count} pages, DPI={_DEFAULT_DPI})"
            )
            return EmbedResult(
                success=True, output_path=output_path,
                message=f"Embedded in page 1/{doc.page_count} (DPI={_DEFAULT_DPI})",
            )
        except Exception as e:
            logger.error(f"PDF embed failed: {e}")
            return EmbedResult(success=False, message=f"PDF embed failed: {e}")
        finally:
            if new_doc:
                new_doc.close()
            if doc:
                doc.close()

    def extract(self, file_path: Path) -> ExtractResult:
        """从 PDF 第一页提取水印。"""
        doc = None
        try:
            doc = fitz.open(str(file_path))
            if doc.page_count == 0:
                return ExtractResult(
                    success=False, confidence=0.0,
                    message="PDF has no pages",
                )
            scale = _DEFAULT_DPI / 72
            mat = fitz.Matrix(scale, scale)
            pix = doc[0].get_pixmap(matrix=mat, alpha=False)
            img = _pixmap_to_bgr(pix)

            payload = _extract_from_image(img, self.strength)
            if payload is None:
                return ExtractResult(
                    success=False, confidence=0.0,
                    message="Failed to extract watermark from PDF",
                )

            logger.info(f"Extracted PDF watermark from {file_path.name}")
            return ExtractResult(
                success=True, payload=payload, confidence=1.0,
                message=f"Employee: {payload.employee_id}",
            )
        except Exception as e:
            logger.error(f"PDF extract failed: {e}")
            return ExtractResult(
                success=False, confidence=0.0,
                message=f"PDF extract failed: {e}",
            )
        finally:
            if doc:
                doc.close()

    def supported_extensions(self) -> list[str]:
        """支持 PDF 格式。"""
        return [".pdf"]


# ==================== 内部工具函数 ====================


def _pixmap_to_bgr(pix: fitz.Pixmap) -> np.ndarray:
    """将 PyMuPDF pixmap (RGB) 转换为 OpenCV BGR numpy 数组。"""
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
        pix.height, pix.width, pix.n,
    )
    return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)


def _add_texture_noise(img: np.ndarray) -> np.ndarray:
    """为纯白页面添加微弱噪声（PSNR≈40dB），提供 DWT-DCT-SVD 所需纹理。"""
    rng = np.random.RandomState(_NOISE_SEED)
    noise = rng.normal(0, _NOISE_SIGMA, img.shape)
    return np.clip(img.astype(np.float64) + noise, 0, 255).astype(np.uint8)


def _embed_to_image(
    img: np.ndarray, bits: list[int],
    strength: WatermarkStrength,
) -> np.ndarray:
    """在 BGR 图像上嵌入 DWT-DCT-SVD 水印，返回水印图像（uint8）。"""
    bwm = WaterMark(password_wm=_PASSWORD_WM, password_img=_PASSWORD_IMG)
    d1, d2 = _STRENGTH_MAP[strength]
    bwm.bwm_core.d1 = d1
    bwm.bwm_core.d2 = d2
    bwm.bwm_core.read_img_arr(img)
    bwm.read_wm(bits, mode="bit")
    result = bwm.embed()
    return np.clip(result, 0, 255).astype(np.uint8)


def _extract_from_image(
    img: np.ndarray, strength: WatermarkStrength,
) -> Optional[WatermarkPayload]:
    """从 BGR 图像提取 DWT-DCT-SVD 水印，返回 payload 或 None。"""
    bwm = WaterMark(password_wm=_PASSWORD_WM, password_img=_PASSWORD_IMG)
    d1, d2 = _STRENGTH_MAP[strength]
    bwm.bwm_core.d1 = d1
    bwm.bwm_core.d2 = d2
    raw = bwm.extract(embed_img=img, wm_shape=_PAYLOAD_BITS, mode="bit")
    bits = (np.array(raw) > 0.5).astype(int).tolist()
    return bits_to_payload(bits)


def _insert_image_page(
    doc: fitz.Document, img: np.ndarray, rect: fitz.Rect,
) -> None:
    """向 PDF 文档添加一页并插入图像。"""
    page = doc.new_page(width=rect.width, height=rect.height)
    # imencode 内部自动 BGR→RGB 转换，直接传 BGR 数组
    success, buf = cv2.imencode(".png", img)
    if not success:
        raise RuntimeError("Failed to encode page image to PNG")
    page.insert_image(page.rect, stream=buf.tobytes())
