"""
Office 文档水印调度器（DOCX/XLSX/PPTX）。

按文件扩展名分发到对应的格式处理器，
所有编解码逻辑集中在此模块，handler 只负责文件读写。
"""

from pathlib import Path

from loguru import logger

from src.watermarks.base import (
    WatermarkBase, WatermarkPayload, EmbedResult, ExtractResult,
)
from src.watermarks.payload_codec import payload_to_bits, bits_to_payload
from src.watermarks.zwc_codec import zwc_encode, zwc_decode
from src.watermarks._docx_handler import embed_docx, extract_docx
from src.watermarks._xlsx_handler import embed_xlsx, extract_xlsx
from src.watermarks._pptx_handler import embed_pptx, extract_pptx

# 扩展名 → (嵌入函数, 提取函数) 映射
_HANDLERS = {
    ".docx": (embed_docx, extract_docx),
    ".xlsx": (embed_xlsx, extract_xlsx),
    ".pptx": (embed_pptx, extract_pptx),
}


class OfficeWatermark(WatermarkBase):
    """Office 文档水印处理器。按格式分发到 DOCX/XLSX/PPTX handler。"""

    def embed(
        self, input_path: Path, payload: WatermarkPayload,
        output_path: Path,
    ) -> EmbedResult:
        """在 Office 文档中嵌入零宽字符水印。"""
        ext = Path(input_path).suffix.lower()
        handler = _HANDLERS.get(ext)
        if handler is None:
            return EmbedResult(
                success=False,
                message=f"Unsupported Office format: {ext}",
            )
        embed_fn, _ = handler

        # 编码水印载荷
        try:
            bits = payload_to_bits(payload)
        except ValueError as e:
            return EmbedResult(success=False, message=str(e))
        zwc_block = zwc_encode(bits)

        # 分发到对应 handler
        success, msg = embed_fn(input_path, zwc_block, output_path)
        if not success:
            return EmbedResult(success=False, message=msg)

        logger.info(f"Office watermark embedded: {input_path.name}")
        return EmbedResult(
            success=True, output_path=output_path,
            message=f"Embedded ZWC watermark ({ext})",
        )

    def extract(self, file_path: Path) -> ExtractResult:
        """从 Office 文档中提取零宽字符水印。"""
        ext = Path(file_path).suffix.lower()
        handler = _HANDLERS.get(ext)
        if handler is None:
            return ExtractResult(
                success=False, confidence=0.0,
                message=f"Unsupported Office format: {ext}",
            )
        _, extract_fn = handler

        # 从 handler 获取全部文本
        text = extract_fn(file_path)
        if text is None:
            return ExtractResult(
                success=False, confidence=0.0,
                message=f"Cannot extract text from {ext} file",
            )

        # 解码 ZWC 水印
        bits = zwc_decode(text)
        if bits is None:
            return ExtractResult(
                success=False, confidence=0.0,
                message="No ZWC watermark found in document",
            )

        payload = bits_to_payload(bits)
        if payload is None:
            return ExtractResult(
                success=False, confidence=0.0,
                message="ZWC found but payload decode failed",
            )

        logger.info(f"Extracted Office watermark from {file_path.name}")
        return ExtractResult(
            success=True, payload=payload, confidence=1.0,
            message=f"Employee: {payload.employee_id}",
        )

    def supported_extensions(self) -> list[str]:
        """支持的 Office 格式。"""
        return [".docx", ".xlsx", ".pptx"]
