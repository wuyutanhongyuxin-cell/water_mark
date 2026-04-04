"""
纯文本零宽字符水印处理器。

在文本文件中嵌入不可见的零宽 Unicode 字符序列，
实现对 TXT/CSV/JSON/MD 文件的盲水印。
肉眼完全不可见，但可通过程序精确提取。
"""

from pathlib import Path

from loguru import logger

from src.watermarks.base import (
    WatermarkBase, WatermarkPayload, EmbedResult, ExtractResult,
)
from src.watermarks.payload_codec import payload_to_bits, bits_to_payload
from src.watermarks.zwc_codec import zwc_encode, zwc_decode

# 文本最小长度（太短的文本嵌入后容易被察觉）
_MIN_TEXT_LENGTH = 10


class TextWatermark(WatermarkBase):
    """纯文本零宽字符水印处理器。支持 TXT/CSV/JSON/MD。"""

    def embed(
        self, input_path: Path, payload: WatermarkPayload,
        output_path: Path,
    ) -> EmbedResult:
        """
        在文本文件中嵌入零宽字符水印。

        根据文件格式选择安全的插入点：
        - JSON: 第一个字符串值内部
        - TXT/CSV/MD: 第一个换行符后
        """
        try:
            content = Path(input_path).read_text(encoding="utf-8")
        except Exception as e:
            return EmbedResult(success=False, message=f"Cannot read file: {e}")

        if len(content) < _MIN_TEXT_LENGTH:
            return EmbedResult(
                success=False,
                message=f"Text too short ({len(content)} chars, min {_MIN_TEXT_LENGTH})",
            )

        # 生成 ZWC 水印块
        try:
            bits = payload_to_bits(payload)
        except ValueError as e:
            return EmbedResult(success=False, message=str(e))
        zwc_block = zwc_encode(bits)

        # 格式感知的插入点选择
        ext = Path(input_path).suffix.lower()
        watermarked = _insert_zwc(content, zwc_block, ext)

        try:
            Path(output_path).write_text(watermarked, encoding="utf-8")
        except Exception as e:
            return EmbedResult(success=False, message=f"Cannot write file: {e}")

        logger.info(f"Text watermark embedded: {input_path.name}")
        return EmbedResult(
            success=True, output_path=output_path,
            message="Embedded ZWC watermark",
        )

    def extract(self, file_path: Path) -> ExtractResult:
        """从文本文件中提取零宽字符水印。"""
        try:
            content = Path(file_path).read_text(encoding="utf-8")
        except Exception as e:
            return ExtractResult(
                success=False, confidence=0.0,
                message=f"Cannot read file: {e}",
            )

        bits = zwc_decode(content)
        if bits is None:
            return ExtractResult(
                success=False, confidence=0.0,
                message="No ZWC watermark found in text",
            )

        payload = bits_to_payload(bits)
        if payload is None:
            return ExtractResult(
                success=False, confidence=0.0,
                message="ZWC found but payload decode failed",
            )

        logger.info(f"Extracted text watermark from {file_path.name}")
        return ExtractResult(
            success=True, payload=payload, confidence=1.0,
            message=f"Employee: {payload.employee_id}",
        )

    def supported_extensions(self) -> list[str]:
        """支持的纯文本格式。"""
        return [".txt", ".csv", ".json", ".md"]


def _insert_zwc(content: str, zwc_block: str, ext: str) -> str:
    """
    格式感知插入零宽字符块。

    JSON 文件：插入到第一个 '": "' 之后的字符串值内部。
    其他文件：插入到第一个换行符之后。
    """
    if ext == ".json":
        marker = '": "'
        idx = content.find(marker)
        if idx != -1:
            pos = idx + len(marker)
            return content[:pos] + zwc_block + content[pos:]
    # 默认：在第一个换行符后插入
    idx = content.find("\n")
    if idx != -1:
        pos = idx + 1
        return content[:pos] + zwc_block + content[pos:]
    # 无换行符：追加到末尾
    return content + zwc_block
