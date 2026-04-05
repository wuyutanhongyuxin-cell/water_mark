"""
异常/攻击检测模块测试。

测试 src.ai.anomaly 的双引擎异常检测：
- _rule_based_check(): 基于置信度的规则引擎
- _merge_results(): AI + 规则结果合并（规则为安全下限）
- _parse_ai_response(): AI JSON 响应解析
- detect_anomaly(): 完整检测流程（AI 禁用时 fallback）
"""

import json

import pytest

from src.ai.ai_types import AnomalyResult
from src.ai.anomaly import (
    _RISK_ORDER,
    _merge_results,
    _parse_ai_response,
    _rule_based_check,
    detect_anomaly,
)
from src.watermarks.base import ExtractResult, WatermarkPayload


# ========== 辅助函数 ==========

def _make_extract_result(
    success: bool = True,
    confidence: float = 0.9,
    employee_id: str = "E001",
) -> ExtractResult:
    """快捷创建 ExtractResult 用于测试。"""
    payload = WatermarkPayload(employee_id=employee_id) if success else None
    return ExtractResult(
        success=success,
        payload=payload,
        confidence=confidence,
    )


# ========== _rule_based_check 测试 ==========

class TestRuleBasedCheck:
    """规则引擎：根据提取结果判定风险等级。"""

    def test_extraction_failed_high_risk(self):
        """提取失败 → 高风险，anomaly_type='watermark_removed'。"""
        result = _rule_based_check(_make_extract_result(success=False))
        assert result.has_anomaly is True
        assert result.risk_level == "high"
        assert result.anomaly_type == "watermark_removed"

    def test_low_confidence_medium_risk(self):
        """置信度 0.3（< 0.5）→ 中风险，anomaly_type='tamper_suspected'。"""
        result = _rule_based_check(_make_extract_result(confidence=0.3))
        assert result.has_anomaly is True
        assert result.risk_level == "medium"
        assert result.anomaly_type == "tamper_suspected"

    def test_mid_confidence_low_risk(self):
        """置信度 0.6（0.5-0.7 之间）→ 低风险，anomaly_type='low_confidence'。"""
        result = _rule_based_check(_make_extract_result(confidence=0.6))
        assert result.has_anomaly is True
        assert result.risk_level == "low"
        assert result.anomaly_type == "low_confidence"

    def test_high_confidence_no_anomaly(self):
        """置信度 0.9（>= 0.7）→ 无异常。"""
        result = _rule_based_check(_make_extract_result(confidence=0.9))
        assert result.has_anomaly is False
        assert result.risk_level == "none"

    def test_boundary_0_5_is_medium(self):
        """置信度恰好 0.5 → 属于 [0.5, 0.7) 区间 → 低风险。"""
        result = _rule_based_check(_make_extract_result(confidence=0.5))
        assert result.risk_level == "low"

    def test_boundary_0_7_is_none(self):
        """置信度恰好 0.7 → >= 0.7 → 无异常。"""
        result = _rule_based_check(_make_extract_result(confidence=0.7))
        assert result.has_anomaly is False


# ========== _merge_results 测试 ==========

class TestMergeResults:
    """AI + 规则结果合并：规则为安全下限。"""

    def test_ai_higher_risk_uses_ai(self):
        """AI 风险更高 → 使用 AI 结果。"""
        rule = AnomalyResult(
            has_anomaly=True, risk_level="low", anomaly_type="low_confidence",
        )
        ai = AnomalyResult(
            has_anomaly=True, risk_level="high", anomaly_type="watermark_removed",
            from_ai=True,
        )
        merged = _merge_results(rule, ai)
        assert merged.risk_level == "high"
        assert merged.from_ai is True

    def test_ai_lower_risk_keeps_rule(self):
        """AI 风险更低 → 保留规则结果（安全下限）。"""
        rule = AnomalyResult(
            has_anomaly=True, risk_level="medium", anomaly_type="tamper_suspected",
        )
        ai = AnomalyResult(
            has_anomaly=False, risk_level="none", from_ai=True,
        )
        merged = _merge_results(rule, ai)
        # 规则判定 medium，AI 判定 none → 保留 medium
        assert merged.risk_level == "medium"
        assert merged.anomaly_type == "tamper_suspected"

    def test_equal_risk_uses_ai(self):
        """风险等级相同 → 使用 AI 结果（描述更详细）。"""
        rule = AnomalyResult(
            has_anomaly=True, risk_level="low",
            description="规则引擎判断",
        )
        ai = AnomalyResult(
            has_anomaly=True, risk_level="low",
            description="AI 详细分析",
            from_ai=True,
        )
        merged = _merge_results(rule, ai)
        assert merged.from_ai is True
        assert "AI" in merged.description


# ========== _parse_ai_response 测试 ==========

class TestParseAiResponse:
    """AI JSON 响应解析。"""

    def test_valid_json_response(self):
        """合法 JSON → 正确解析，from_ai=True。"""
        response = json.dumps({
            "has_anomaly": True,
            "anomaly_type": "tamper_suspected",
            "risk_level": "medium",
            "description": "检测到篡改迹象",
            "recommendations": ["核查来源", "比对原文件"],
        })
        result = _parse_ai_response(response)
        assert result.from_ai is True
        assert result.has_anomaly is True
        assert result.risk_level == "medium"
        assert result.anomaly_type == "tamper_suspected"
        assert len(result.recommendations) == 2

    def test_invalid_json_returns_default(self):
        """无效 JSON → from_ai=False（触发 fallback）。"""
        result = _parse_ai_response("This is not JSON at all")
        assert result.from_ai is False

    def test_invalid_risk_level_defaults_to_none(self):
        """risk_level 不在合法范围 → 默认为 'none'。"""
        response = json.dumps({
            "has_anomaly": False,
            "risk_level": "critical",  # 非法值
        })
        result = _parse_ai_response(response)
        assert result.risk_level == "none"


# ========== detect_anomaly 完整流程测试 ==========

class TestDetectAnomaly:
    """完整异常检测流程（AI 在测试中禁用，conftest 的 disable_ai 生效）。"""

    def test_ai_disabled_returns_rule_result(self):
        """AI 禁用 → 直接返回规则引擎结果。"""
        extract = _make_extract_result(confidence=0.6)
        result = detect_anomaly(extract, file_name="test.png")
        # 0.6 在 [0.5, 0.7) 区间 → low risk
        assert result.risk_level == "low"
        assert result.anomaly_type == "low_confidence"
        # 不应标记为 AI 结果
        assert result.from_ai is False

    def test_extraction_failed_high_risk(self):
        """提取失败 → 高风险，不调用 AI。"""
        extract = _make_extract_result(success=False)
        result = detect_anomaly(extract, file_name="damaged.pdf")
        assert result.risk_level == "high"
        assert result.anomaly_type == "watermark_removed"
        assert result.has_anomaly is True

    def test_high_confidence_no_anomaly(self):
        """高置信度 → 无异常。"""
        extract = _make_extract_result(confidence=0.95)
        result = detect_anomaly(extract, file_name="clean.docx")
        assert result.has_anomaly is False
        assert result.risk_level == "none"


# ========== 常量验证 ==========

class TestConstants:
    """验证风险等级排序常量。"""

    def test_risk_order_values(self):
        """_RISK_ORDER 的排序：none < low < medium < high。"""
        assert _RISK_ORDER["none"] < _RISK_ORDER["low"]
        assert _RISK_ORDER["low"] < _RISK_ORDER["medium"]
        assert _RISK_ORDER["medium"] < _RISK_ORDER["high"]

    def test_risk_order_has_all_levels(self):
        """_RISK_ORDER 应包含四个等级。"""
        assert set(_RISK_ORDER.keys()) == {"none", "low", "medium", "high"}
