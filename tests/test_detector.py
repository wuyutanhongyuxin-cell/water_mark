"""
文件类型检测模块测试。

测试 src.core.detector 的双重验证逻辑：
- magic bytes + 扩展名一致 → confidence=1.0
- 不一致 → 以 magic bytes 为准，confidence=0.8
- OOXML 特判（.docx/.xlsx/.pptx 识别为 ZIP）
- 文件不存在 → FileNotFoundError
- 未知类型 → category="unknown", confidence=0.0
"""

import shutil
from pathlib import Path

import pytest

from src.core.detector import (
    DetectionResult,
    EXT_TO_MIME,
    FILE_CATEGORIES,
    detect_file_type,
)


# ========== 辅助函数 ==========

def _assert_detection(result: DetectionResult, category: str, **kwargs):
    """通用断言：检查 category 和可选字段。"""
    assert result.category == category, (
        f"Expected category '{category}', got '{result.category}'"
    )
    for key, expected in kwargs.items():
        actual = getattr(result, key)
        assert actual == expected, (
            f"Field '{key}': expected {expected!r}, got {actual!r}"
        )


# ========== 基本类型检测 ==========

class TestBasicDetection:
    """常见文件类型的正常检测。"""

    def test_detect_png_image(self, sample_image):
        """PNG 图像：category=image, mime=image/png, confidence=1.0。"""
        result = detect_file_type(sample_image)
        _assert_detection(result, "image", mime_type="image/png", confidence=1.0)
        assert result.extension == ".png"

    def test_detect_txt_file(self, sample_txt):
        """纯文本文件：category=text。"""
        result = detect_file_type(sample_txt)
        _assert_detection(result, "text")
        assert result.extension == ".txt"

    def test_detect_pdf_file(self, sample_pdf):
        """PDF 文件：category=pdf。"""
        result = detect_file_type(sample_pdf)
        _assert_detection(result, "pdf")
        assert result.mime_type == "application/pdf"

    def test_detect_wav_audio(self, sample_wav):
        """WAV 音频：category=audio。"""
        result = detect_file_type(sample_wav)
        _assert_detection(result, "audio")

    def test_detect_avi_video(self, sample_avi):
        """AVI 视频：category=video。"""
        result = detect_file_type(sample_avi)
        _assert_detection(result, "video")


# ========== OOXML 特判（ZIP 容器） ==========

class TestOoxmlSpecialCase:
    """Office 文件的 magic bytes 是 ZIP，需要特判处理。"""

    def test_detect_docx(self, sample_docx):
        """DOCX 文件：magic=ZIP → OOXML override → category=office_word。"""
        result = detect_file_type(sample_docx)
        _assert_detection(result, "office_word")
        assert result.extension == ".docx"

    def test_detect_xlsx(self, sample_xlsx):
        """XLSX 文件：magic=ZIP → OOXML override → category=office_excel。"""
        result = detect_file_type(sample_xlsx)
        _assert_detection(result, "office_excel")
        assert result.extension == ".xlsx"

    def test_detect_pptx(self, sample_pptx):
        """PPTX 文件：magic=ZIP → OOXML override → category=office_pptx。"""
        result = detect_file_type(sample_pptx)
        _assert_detection(result, "office_pptx")
        assert result.extension == ".pptx"


# ========== 边界情况 ==========

class TestEdgeCases:
    """边界条件和异常情况。"""

    def test_unknown_file_type(self, tmp_path):
        """未知类型：随机字节 + 未知扩展名 → category=unknown。"""
        unknown_file = tmp_path / "data.xyz"
        # 写入随机字节，确保扩展名无法识别
        unknown_file.write_bytes(b"\xfe\xed\xfa\xce" * 100)
        result = detect_file_type(unknown_file)
        # magic 可能检测出某种 MIME（如 octet-stream），但 category 应为 unknown
        assert result.category == "unknown"

    def test_file_not_found(self, tmp_path):
        """文件不存在 → FileNotFoundError。"""
        missing = tmp_path / "no_such_file.png"
        with pytest.raises(FileNotFoundError):
            detect_file_type(missing)

    def test_extension_mismatch(self, sample_image, tmp_path):
        """扩展名不匹配：.png → .txt，magic bytes 为准，confidence=0.8。"""
        # 把 PNG 图像重命名为 .txt 扩展名
        renamed = tmp_path / "fake_text.txt"
        shutil.copy2(sample_image, renamed)

        result = detect_file_type(renamed)
        # magic bytes 检测到 image/png，以此为准
        assert result.mime_type == "image/png"
        assert result.category == "image"
        assert result.confidence == 0.8
        assert result.warning  # 不一致时应有告警


# ========== 数据结构验证 ==========

class TestDataStructures:
    """FILE_CATEGORIES 和 EXT_TO_MIME 的完整性。"""

    def test_file_categories_has_all_types(self):
        """FILE_CATEGORIES 应包含所有八大类别。"""
        expected = {
            "image", "pdf", "office_word", "office_excel",
            "office_pptx", "audio", "video", "text",
        }
        assert expected == set(FILE_CATEGORIES.keys())

    def test_ext_to_mime_has_common_extensions(self):
        """EXT_TO_MIME 应包含常用扩展名。"""
        for ext in (".png", ".pdf", ".docx", ".xlsx", ".pptx", ".wav", ".txt"):
            assert ext in EXT_TO_MIME, f"Missing extension: {ext}"

    def test_detection_result_defaults(self):
        """DetectionResult 默认值：confidence=1.0, warning=""。"""
        r = DetectionResult(mime_type="text/plain", category="text", extension=".txt")
        assert r.confidence == 1.0
        assert r.warning == ""
