"""
AI 模块共享的输入清洗工具。

防止 prompt injection：截断、去控制字符、白名单过滤。
"""

import re

# 控制字符正则（U+0000-U+001F, U+007F-U+009F）
_CTRL_CHARS = re.compile(r"[\x00-\x1f\x7f-\x9f]")

# 员工 ID 白名单：只允许字母数字和连字符下划线
_SAFE_ID = re.compile(r"[^a-zA-Z0-9\-_]")


def sanitize_for_prompt(text: str, max_len: int = 100) -> str:
    """清洗文本用于 AI 提示词：去控制字符 + 截断。"""
    cleaned = _CTRL_CHARS.sub("", text)
    return cleaned[:max_len]


def sanitize_employee_id(emp_id: str, max_len: int = 32) -> str:
    """清洗员工 ID：只保留安全字符，不合法内容替换为 '?'。"""
    cleaned = _SAFE_ID.sub("?", str(emp_id))
    return cleaned[:max_len] if cleaned else "REDACTED"
