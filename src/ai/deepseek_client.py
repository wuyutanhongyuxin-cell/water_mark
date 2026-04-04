"""
DeepSeek API 客户端。

使用 OpenAI 兼容 SDK 调用 DeepSeek，提供懒加载和审计日志。
重试由 OpenAI SDK 的 max_retries 参数控制（传入配置值）。
所有调用失败时返回 None（graceful degradation），不影响核心水印功能。
"""

import os
import time
import threading
from typing import Optional

from loguru import logger

# 懒加载：OpenAI 客户端实例
_client = None
_client_lock = threading.Lock()


def _get_ai_config() -> dict:
    """从 settings.yaml 读取 AI 配置段。延迟导入避免循环依赖。"""
    from src.core.router import load_settings
    settings = load_settings()
    return settings.get("ai", {})


def is_ai_enabled() -> bool:
    """检查 AI 功能是否启用（配置开关 + API Key 存在）。"""
    config = _get_ai_config()
    if not config.get("enabled", False):
        return False
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        logger.debug("AI enabled in config but DEEPSEEK_API_KEY not set")
        return False
    return True


def _get_client():
    """懒加载 OpenAI 客户端（线程安全）。"""
    global _client
    if _client is not None:
        return _client
    with _client_lock:
        if _client is not None:
            return _client
        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        if not api_key:
            return None
        config = _get_ai_config()
        try:
            from openai import OpenAI
            _client = OpenAI(
                api_key=api_key,
                base_url=config.get("base_url", "https://api.deepseek.com"),
                timeout=config.get("timeout", 30),
                max_retries=config.get("max_retries", 2),
            )
            return _client
        except Exception as e:
            logger.warning(f"Failed to create OpenAI client: {e}")
            return None


def reset_client() -> None:
    """重置客户端（测试用）。"""
    global _client
    with _client_lock:
        _client = None


def call_deepseek(
    system_prompt: str,
    user_prompt: str,
    json_mode: bool = True,
    model_override: Optional[str] = None,
) -> Optional[str]:
    """
    调用 DeepSeek API。失败返回 None（graceful degradation）。

    Args:
        system_prompt: 系统提示词
        user_prompt: 用户提示词
        json_mode: 是否要求 JSON 格式输出
        model_override: 覆盖默认模型名

    Returns:
        API 响应文本，失败时返回 None
    """
    # 延迟导入审计模块，避免循环依赖
    from src.security.audit import log_ai_call

    if not is_ai_enabled():
        return None

    client = _get_client()
    if client is None:
        return None

    config = _get_ai_config()
    model = model_override or config.get("model", "deepseek-chat")
    temperature = config.get("temperature", 0.3)

    # 构建请求参数
    kwargs = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    start = time.monotonic()
    try:
        response = client.chat.completions.create(**kwargs)
        latency = time.monotonic() - start
        content = response.choices[0].message.content or ""
        tokens = getattr(response.usage, "total_tokens", 0) if response.usage else 0

        log_ai_call(
            operation="deepseek_chat", model=model,
            input_summary=f"[{len(user_prompt)} chars]",
            output_summary=f"[{len(content)} chars]",
            tokens=tokens, latency=latency, success=True,
        )
        return content

    except Exception as e:
        latency = time.monotonic() - start
        # 只记录异常类型名，不记录完整 str(e)（可能包含 API Key / Auth header）
        error_type = type(e).__name__
        logger.warning(f"DeepSeek API call failed ({latency:.1f}s): {error_type}")
        log_ai_call(
            operation="deepseek_chat", model=model,
            input_summary=f"[{len(user_prompt)} chars]",
            output_summary=f"error:{error_type}",
            tokens=0, latency=latency, success=False,
        )
        return None
