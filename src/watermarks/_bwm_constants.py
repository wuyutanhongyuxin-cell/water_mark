"""
blind-watermark 共享常量（image_wm / _video_core 共用）。

DWT-DCT-SVD 嵌入的密码种子和强度参数。
单一来源，避免两个文件各自定义相同常量导致同步遗漏。
"""

from src.watermarks.base import WatermarkStrength

# 固定密码种子（blind-watermark 内部参数）
PASSWORD_WM = 20260403
PASSWORD_IMG = 20260403

# 嵌入强度映射：(d1, d2) — 越大越鲁棒但 PSNR 越低
STRENGTH_MAP = {
    WatermarkStrength.LOW: (15, 8),       # PSNR ~44dB
    WatermarkStrength.MEDIUM: (36, 20),   # PSNR ~34dB (1024-bit)
    WatermarkStrength.HIGH: (64, 36),     # PSNR ~30dB
}
