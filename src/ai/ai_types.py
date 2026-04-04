"""
AI 结果数据类型定义。

所有 AI 分析函数的返回值类型，确保统一的接口契约。
AI 不可用时使用 dataclass 默认值（graceful degradation）。
"""

from dataclasses import dataclass, field


@dataclass
class SensitivityResult:
    """
    文件敏感度分析结果。

    Attributes:
        recommended_strength: 推荐水印强度 ("low"/"medium"/"high")
        sensitivity_level: 敏感度等级 (1-5)
        reasoning: AI 分析理由
        strategy_notes: 策略建议说明
        from_ai: True=AI 生成, False=默认值
    """
    recommended_strength: str = "medium"
    sensitivity_level: int = 3
    reasoning: str = ""
    strategy_notes: str = ""
    from_ai: bool = False


@dataclass
class AnomalyResult:
    """
    异常/攻击检测结果。

    Attributes:
        has_anomaly: 是否检测到异常
        anomaly_type: 异常类型标识
        risk_level: 风险等级 ("none"/"low"/"medium"/"high")
        description: 异常描述
        recommendations: 建议操作列表
        from_ai: True=AI 生成, False=规则引擎
    """
    has_anomaly: bool = False
    anomaly_type: str = ""
    risk_level: str = "none"
    description: str = ""
    recommendations: list[str] = field(default_factory=list)
    from_ai: bool = False
