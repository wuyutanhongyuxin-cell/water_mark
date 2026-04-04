"""
异常/攻击检测模块（AI + 规则双引擎）。

分析水印提取结果，检测潜在的攻击或篡改。
规则引擎始终执行，AI 作为可选增强。AI 不可用时 fallback 到规则引擎。
AI 结果不允许降低规则引擎的风险判定（规则结果为安全下限）。
"""

import json

from loguru import logger

from src.ai.ai_types import AnomalyResult
from src.ai.deepseek_client import is_ai_enabled, call_deepseek
from src.ai._sanitize import sanitize_for_prompt, sanitize_employee_id
from src.watermarks.base import ExtractResult

# 置信度阈值常量
_CONFIDENCE_MEDIUM_RISK = 0.5  # 低于此值 → 中风险
_CONFIDENCE_LOW_RISK = 0.7     # 低于此值 → 低风险

# 风险等级排序（用于合并时取 max）
_RISK_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3}

# 系统提示词：指导 AI 分析异常
_SYSTEM_PROMPT = """你是企业文档安全专家。分析水印提取结果，检测潜在攻击或篡改。返回 JSON：
{
  "has_anomaly": true 或 false,
  "anomaly_type": "异常类型标识",
  "risk_level": "none" 或 "low" 或 "medium" 或 "high",
  "description": "异常描述",
  "recommendations": ["建议1", "建议2"]
}
异常类型：
- "low_confidence": 置信度偏低，可能有轻微损坏
- "tamper_suspected": 疑似人为篡改
- "watermark_removed": 水印可能已被去除
- "format_attack": 格式转换攻击
- "none": 无异常"""


def _rule_based_check(result: ExtractResult) -> AnomalyResult:
    """本地规则引擎：基于置信度和提取状态判断异常。始终执行。"""
    # 提取失败 → 高风险
    if not result.success:
        return AnomalyResult(
            has_anomaly=True,
            anomaly_type="watermark_removed",
            risk_level="high",
            description="水印提取失败，可能已被去除或文件严重损坏",
            recommendations=["核查文件来源", "与原始文件比对", "检查文件格式是否被转换"],
        )

    confidence = result.confidence

    # 置信度 < 0.5 → 中风险
    if confidence < _CONFIDENCE_MEDIUM_RISK:
        return AnomalyResult(
            has_anomaly=True,
            anomaly_type="tamper_suspected",
            risk_level="medium",
            description=f"水印置信度偏低 ({confidence:.2f})，疑似被攻击或篡改",
            recommendations=["检查文件是否经过压缩或格式转换", "与原始文件比对哈希值"],
        )

    # 置信度 0.5-0.7 → 低风险
    if confidence < _CONFIDENCE_LOW_RISK:
        return AnomalyResult(
            has_anomaly=True,
            anomaly_type="low_confidence",
            risk_level="low",
            description=f"水印置信度一般 ({confidence:.2f})，可能有轻微损坏",
            recommendations=["建议保留原始文件备份"],
        )

    # 置信度 >= 0.7 → 无异常
    return AnomalyResult(has_anomaly=False)


def _parse_ai_response(content: str) -> AnomalyResult:
    """解析 AI JSON 响应。解析失败返回 AnomalyResult(from_ai=False) 以触发 fallback。"""
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return AnomalyResult()

    risk = data.get("risk_level", "none")
    if risk not in ("none", "low", "medium", "high"):
        risk = "none"

    # 严格布尔解析：只接受 True/False，字符串 "false" 不算 True
    raw_anomaly = data.get("has_anomaly", False)
    if isinstance(raw_anomaly, bool):
        has_anomaly = raw_anomaly
    elif isinstance(raw_anomaly, str):
        has_anomaly = raw_anomaly.lower() == "true"
    else:
        has_anomaly = False

    recs = data.get("recommendations", [])
    if not isinstance(recs, list):
        recs = []
    recs = [str(r)[:200] for r in recs[:5]]  # 限制条目数和长度

    return AnomalyResult(
        has_anomaly=has_anomaly,
        anomaly_type=str(data.get("anomaly_type", ""))[:50],
        risk_level=risk,
        description=str(data.get("description", ""))[:300],
        recommendations=recs,
        from_ai=True,
    )


def _merge_results(rule: AnomalyResult, ai: AnomalyResult) -> AnomalyResult:
    """合并规则引擎和 AI 结果：规则结果为安全下限，AI 只能升级不能降级。"""
    rule_rank = _RISK_ORDER.get(rule.risk_level, 0)
    ai_rank = _RISK_ORDER.get(ai.risk_level, 0)

    # 取两者中更高的风险等级
    if ai_rank >= rule_rank:
        # AI 判断风险 ≥ 规则 → 使用 AI 结果（更详细的描述）
        return ai
    # AI 判断风险 < 规则 → 保留规则结果（AI 不允许降级安全判定）
    logger.info(
        f"AI suggested lower risk ({ai.risk_level}) than rules ({rule.risk_level}), "
        f"keeping rule-based result as safety floor"
    )
    return rule


def detect_anomaly(
    result: ExtractResult,
    file_name: str = "",
) -> AnomalyResult:
    """
    检测水印提取结果中的异常。

    双引擎：规则引擎始终执行，AI 作为可选增强。
    AI 结果不允许降低规则引擎的风险判定。

    Args:
        result: 水印提取结果
        file_name: 文件名（用于 AI 分析上下文）

    Returns:
        AnomalyResult: 异常检测结果
    """
    # 1. 规则引擎（始终执行）
    rule_result = _rule_based_check(result)

    # 2. AI 增强（可选）
    if not is_ai_enabled():
        return rule_result

    # 提取失败时规则引擎已判定高风险，无需调 AI（节约成本+防降级）
    if not result.success:
        return rule_result

    # 构建提示词（仅元数据，清洗所有外部输入防 prompt injection）
    safe_name = sanitize_for_prompt(file_name)
    safe_emp_id = sanitize_employee_id(
        result.payload.employee_id if result.payload else "N/A"
    )
    user_prompt = (
        f"分析水印提取结果：\n"
        f"- 文件名: {safe_name}\n"
        f"- 提取成功: {result.success}\n"
        f"- 置信度: {result.confidence:.2f}\n"
        f"- 员工ID: {safe_emp_id}\n"
        f"- 规则引擎判断: {rule_result.anomaly_type or '无异常'} "
        f"(风险={rule_result.risk_level})\n"
        f"请返回 JSON 格式结果。"
    )

    response = call_deepseek(
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        json_mode=True,
    )

    if response is None:
        return rule_result  # AI 不可用 → fallback 到规则引擎

    ai_result = _parse_ai_response(response)
    if ai_result.from_ai:
        merged = _merge_results(rule_result, ai_result)
        logger.info(
            f"AI anomaly: {safe_name} → "
            f"{merged.anomaly_type} ({merged.risk_level})"
        )
        return merged

    # AI 响应解析失败 → fallback
    return rule_result
