"""
水印处理器抽象基类（策略模式）。

所有文件类型的水印处理器必须继承 WatermarkBase，
实现 embed / extract / supported_extensions 三个核心方法。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional
import datetime


class WatermarkStrength(Enum):
    """水印嵌入强度等级。"""
    LOW = "low"          # 低强度：最高隐匿性，较低鲁棒性
    MEDIUM = "medium"    # 中强度：平衡隐匿性与鲁棒性（默认）
    HIGH = "high"        # 高强度：最高鲁棒性，可能略微影响质量


@dataclass
class WatermarkPayload:
    """
    水印载荷数据结构。

    嵌入到文件中的实际信息，包含追踪泄露所需的全部字段。
    序列化为 JSON 后经 AES-256 加密再嵌入。

    Attributes:
        employee_id: 员工唯一标识（如 E001）
        timestamp: 嵌入时间戳（ISO 8601 格式）
        file_hash: 原始文件的 SHA-256 哈希（前16位）
        custom_data: 自定义附加信息
    """
    employee_id: str
    timestamp: str = ""
    file_hash: str = ""
    custom_data: dict = field(default_factory=dict)

    def __post_init__(self):
        """自动填充 UTC 时间戳（如果未提供）。"""
        if not self.timestamp:
            self.timestamp = datetime.datetime.now(
                datetime.timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class EmbedResult:
    """
    水印嵌入结果。

    Attributes:
        success: 是否成功
        output_path: 输出文件路径
        message: 结果描述信息
        quality_metrics: 质量指标（PSNR、SSIM 等）
        elapsed_time: 耗时（秒）
    """
    success: bool
    output_path: Optional[Path] = None
    message: str = ""
    quality_metrics: dict = field(default_factory=dict)
    elapsed_time: float = 0.0


@dataclass
class ExtractResult:
    """
    水印提取结果。

    Attributes:
        success: 是否成功提取
        payload: 提取到的水印载荷（解密后）
        confidence: 提取置信度 (0.0 ~ 1.0)
        message: 结果描述信息
    """
    success: bool
    payload: Optional[WatermarkPayload] = None
    confidence: float = 0.0
    message: str = ""


class WatermarkBase(ABC):
    """
    水印处理器抽象基类。

    所有具体水印处理器必须实现以下方法：
    - embed(): 将水印嵌入文件
    - extract(): 从文件中提取水印
    - verify(): 嵌入后立即验证水印完整性

    子类还可覆写：
    - supported_extensions(): 返回支持的文件扩展名
    - validate_file(): 文件预检查
    """

    def __init__(self, strength: WatermarkStrength = WatermarkStrength.MEDIUM):
        """
        初始化水印处理器。

        Args:
            strength: 水印嵌入强度，默认中等
        """
        self.strength = strength

    @abstractmethod
    def embed(
        self,
        input_path: Path,
        payload: WatermarkPayload,
        output_path: Path,
    ) -> EmbedResult:
        """
        将水印嵌入文件。

        Args:
            input_path: 原始文件路径
            payload: 水印载荷数据
            output_path: 输出文件路径

        Returns:
            EmbedResult: 嵌入结果（含成功标志、质量指标等）

        Raises:
            FileNotFoundError: 输入文件不存在
            ValueError: 载荷数据无效
        """

    @abstractmethod
    def extract(self, file_path: Path) -> ExtractResult:
        """
        从文件中提取水印。

        Args:
            file_path: 待提取的文件路径

        Returns:
            ExtractResult: 提取结果（含载荷、置信度等）

        Raises:
            FileNotFoundError: 文件不存在
        """

    def verify(
        self,
        file_path: Path,
        expected_payload: WatermarkPayload,
    ) -> bool:
        """
        验证文件中的水印是否与预期一致。

        嵌入后必须调用此方法确认水印正确嵌入。
        默认实现：提取水印并比对 employee_id + timestamp。
        子类可覆写以实现更精确的验证逻辑。

        Args:
            file_path: 已嵌入水印的文件路径
            expected_payload: 预期的水印载荷

        Returns:
            bool: 水印验证通过返回 True
        """
        result = self.extract(file_path)
        if not result.success or result.payload is None:
            return False
        # 核心字段比对：员工ID + 时间戳
        return (
            result.payload.employee_id == expected_payload.employee_id
            and result.payload.timestamp == expected_payload.timestamp
        )

    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """
        返回此处理器支持的文件扩展名列表。

        Returns:
            list[str]: 扩展名列表，如 ['.jpg', '.png', '.bmp']
        """

    def validate_file(self, file_path: Path) -> bool:
        """
        预检查文件是否可处理。

        默认实现：检查文件存在且扩展名在支持列表中。
        子类可覆写以添加更多检查（如文件大小、格式完整性）。

        Args:
            file_path: 待检查的文件路径

        Returns:
            bool: 文件可处理返回 True
        """
        if not file_path.exists() or not file_path.is_file():
            return False
        return file_path.suffix.lower() in self.supported_extensions()
