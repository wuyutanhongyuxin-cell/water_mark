"""
文件敏感度分析 + 水印策略建议。

根据文件元数据（不含文件内容）分析敏感度，
推荐水印嵌入强度和策略。AI 不可用时返回安全默认值。
"""

import json
from pathlib import Path

from loguru import logger

from src.ai.ai_types import SensitivityResult
from src.ai.deepseek_client import is_ai_enabled, call_deepseek
from src.ai._sanitize import sanitize_for_prompt

# 系统提示词：指导 AI 分析文件敏感度
_SYSTEM_PROMPT = """你是企业文档安全分析师。根据文件元数据分析敏感度，返回 JSON：
{
  "recommended_strength": "low" 或 "medium" 或 "high",
  "sensitivity_level": 1到5的整数,
  "reasoning": "一句话理由",
  "strategy_notes": "额外建议"
}
评判标准：
- 财务/合同/法律/HR/薪资/机密 → 4-5, high
- 技术文档/内部报告/设计稿 → 3, medium
- 公开资料/模板/示例 → 1-2, low
仅根据文件名、类型和大小推断，不要要求查看文件内容。"""


def _sanitize_filename(name: str) -> str:
    """清洗文件名：截断 + 去除控制字符（防 prompt injection）。"""
    return sanitize_for_prompt(name, max_len=100)


def _build_user_prompt(
    file_name: str, category: str, mime_type: str,
    size_mb: float, extension: str,
) -> str:
    """构建用户提示词（仅元数据，不含文件内容）。"""
    return (
        f"分析以下文件：\n"
        f"- 文件名: {file_name}\n"
        f"- 类型: {category} ({mime_type})\n"
        f"- 大小: {size_mb:.2f} MB\n"
        f"- 扩展名: {extension}\n"
        f"请返回 JSON 格式结果。"
    )


def _parse_response(content: str) -> SensitivityResult:
    """解析 AI JSON 响应，严格校验每个字段。解析失败返回默认值。"""
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        logger.warning("AI response is not valid JSON, using defaults")
        return SensitivityResult()

    # 校验 recommended_strength
    strength = data.get("recommended_strength", "medium")
    if strength not in ("low", "medium", "high"):
        strength = "medium"

    # 校验 sensitivity_level
    level = data.get("sensitivity_level", 3)
    try:
        level = int(level)
        level = max(1, min(5, level))  # 钳制到 1-5
    except (ValueError, TypeError):
        level = 3

    reasoning = str(data.get("reasoning", ""))[:200]
    strategy = str(data.get("strategy_notes", ""))[:200]

    return SensitivityResult(
        recommended_strength=strength,
        sensitivity_level=level,
        reasoning=reasoning,
        strategy_notes=strategy,
        from_ai=True,
    )


def analyze_sensitivity(file_path: Path) -> SensitivityResult:
    """
    分析文件敏感度并推荐水印策略。

    AI 不可用时返回默认 SensitivityResult(from_ai=False)。
    仅发送文件元数据给 API，不发送文件内容。

    Args:
        file_path: 待分析的文件路径

    Returns:
        SensitivityResult: 敏感度分析结果
    """
    # AI 未启用 → 返回默认值
    if not is_ai_enabled():
        return SensitivityResult()

    # 获取文件元数据
    file_path = Path(file_path)
    try:
        from src.core.detector import detect_file_type
        detection = detect_file_type(file_path)
    except Exception as e:
        logger.warning(f"File detection failed for sensitivity analysis: {e}")
        return SensitivityResult()

    # 构建提示词
    file_name = _sanitize_filename(file_path.name)
    try:
        size_mb = file_path.stat().st_size / (1024 * 1024)
    except OSError:
        logger.warning(f"Cannot stat file for sensitivity analysis: {file_path}")
        return SensitivityResult()
    user_prompt = _build_user_prompt(
        file_name=file_name,
        category=detection.category,
        mime_type=detection.mime_type,
        size_mb=size_mb,
        extension=detection.extension,
    )

    # 调用 DeepSeek API
    response = call_deepseek(
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        json_mode=True,
    )

    if response is None:
        logger.info("AI sensitivity analysis unavailable, using defaults")
        return SensitivityResult()

    # 解析并返回结果
    result = _parse_response(response)
    logger.info(
        f"AI sensitivity: {file_path.name} → "
        f"strength={result.recommended_strength}, "
        f"level={result.sensitivity_level}"
    )
    return result
