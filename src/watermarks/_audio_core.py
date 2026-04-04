"""
音频水印核心算法（纯数值计算，无文件 I/O）。

1D Haar DWT → DCT → QIM 量化调制嵌入/提取。
嵌入在 detail 系数的 DCT 域，对听感影响最小。
"""

import numpy as np
from scipy.fft import dct, idct


# 强度 → QIM 量化步长映射
DELTA_MAP = {
    "low": 0.005,       # SNR ~45dB，最高隐匿性
    "medium": 0.02,     # SNR ~35dB，平衡（默认）
    "high": 0.05,       # SNR ~28dB，最高鲁棒性
}

# 固定载荷大小（与 payload_codec 一致）
_PAYLOAD_BITS = 1024


def haar_dwt(signal: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """1D Haar 小波分解 → (近似系数 approx, 细节系数 detail)。"""
    n = len(signal)
    half = n // 2
    inv_sqrt2 = 1.0 / np.sqrt(2.0)
    # 向量化计算：偶数索引和奇数索引配对
    even = signal[0:2 * half:2]
    odd = signal[1:2 * half:2]
    approx = (even + odd) * inv_sqrt2
    detail = (even - odd) * inv_sqrt2
    return approx, detail


def haar_idwt(approx: np.ndarray, detail: np.ndarray) -> np.ndarray:
    """1D Haar 逆小波变换 → 重建信号。"""
    n = len(approx)
    inv_sqrt2 = 1.0 / np.sqrt(2.0)
    signal = np.empty(2 * n, dtype=np.float64)
    signal[0::2] = (approx + detail) * inv_sqrt2
    signal[1::2] = (approx - detail) * inv_sqrt2
    return signal


def _qim_embed_bit(value: float, bit: int, delta: float) -> float:
    """QIM 量化调制：将单个 bit 嵌入一个 DCT 系数。偶数网格=0，奇数网格=1。"""
    if delta <= 0:
        raise ValueError(f"delta must be positive, got {delta}")
    index = round(value / delta)
    if index % 2 != bit:
        # 移到最近的匹配网格点
        if value >= index * delta:
            index += 1
        else:
            index -= 1
    return index * delta


def _qim_extract_bit(value: float, delta: float) -> int:
    """QIM 提取：从 DCT 系数中读取嵌入的 bit。"""
    index = round(value / delta)
    return abs(index) % 2


def embed_audio_signal(
    signal: np.ndarray, bits: list[int], delta: float,
) -> np.ndarray:
    """
    在音频信号中嵌入 1024-bit 水印。

    流程：Haar DWT → detail 系数分块 → DCT → QIM 修改 DC → IDCT → IDWT

    Args:
        signal: 1D 音频信号（float64, 归一化 [-1, 1]）
        bits: 1024-bit 水印数组
        delta: QIM 量化步长（由强度等级决定）

    Returns:
        水印信号（同长度 float64）
    """
    if len(bits) != _PAYLOAD_BITS:
        raise ValueError(f"Expected {_PAYLOAD_BITS} bits, got {len(bits)}")

    work = signal.astype(np.float64).copy()

    # Haar DWT 要求偶数长度
    padded = len(work) % 2 != 0
    if padded:
        work = np.append(work, 0.0)

    approx, detail = haar_dwt(work)

    # 分块大小：detail 长度 / 1024，最小 32
    block_size = max(32, len(detail) // _PAYLOAD_BITS)

    for i in range(_PAYLOAD_BITS):
        start = i * block_size
        end = min(start + block_size, len(detail))
        if start >= len(detail):
            break
        block = detail[start:end].copy()
        dct_block = dct(block, type=2, norm='ortho')
        # QIM 修改 DC 系数（第0个）
        dct_block[0] = _qim_embed_bit(dct_block[0], bits[i], delta)
        detail[start:end] = idct(dct_block, type=2, norm='ortho')

    result = haar_idwt(approx, detail)
    if padded:
        result = result[:-1]
    return result


def extract_audio_signal(
    signal: np.ndarray, delta: float,
) -> list[int]:
    """
    从音频信号中提取 1024-bit 水印。

    Args:
        signal: 水印音频信号
        delta: QIM 量化步长（必须与嵌入时一致）

    Returns:
        1024-bit 水印数组
    """
    work = signal.astype(np.float64).copy()
    if len(work) % 2 != 0:
        work = np.append(work, 0.0)

    _, detail = haar_dwt(work)
    block_size = max(32, len(detail) // _PAYLOAD_BITS)

    bits = []
    for i in range(_PAYLOAD_BITS):
        start = i * block_size
        end = min(start + block_size, len(detail))
        if start >= len(detail):
            bits.append(0)
            continue
        block = detail[start:end]
        dct_block = dct(block, type=2, norm='ortho')
        bits.append(_qim_extract_bit(dct_block[0], delta))

    return bits


def calc_snr(original: np.ndarray, watermarked: np.ndarray) -> float:
    """计算信噪比 SNR（dB）。值越高水印越不可察觉。"""
    noise = watermarked.astype(np.float64) - original.astype(np.float64)
    signal_power = np.mean(original.astype(np.float64) ** 2)
    noise_power = np.mean(noise ** 2)
    if signal_power < 1e-20:
        return 0.0   # 全静音信号，SNR 无意义
    if noise_power < 1e-20:
        return 99.0  # 几乎无噪声
    return float(10 * np.log10(signal_power / noise_power))
