# ai — AI 集成模块

## 用途
DeepSeek API 集成，为水印操作提供 AI 增强：敏感度分析、策略建议、异常检测。

## 架构
```
ai_types.py ──────── 数据类型定义（无依赖）
_sanitize.py ─────── 共享输入清洗工具（防 prompt injection）
deepseek_client.py ── API 客户端（懒加载 + 审计）
sensitivity.py ───── 文件敏感度分析 + 策略建议
anomaly.py ────────── 异常/攻击检测（AI + 规则双引擎）
__init__.py ───────── 公共 API 导出
```

## 文件清单
- `ai_types.py` — SensitivityResult + AnomalyResult 数据类（~48行）
- `_sanitize.py` — 共享清洗函数：sanitize_for_prompt + sanitize_employee_id（~25行）
- `deepseek_client.py` — OpenAI 兼容客户端，懒加载+审计（~143行）
- `sensitivity.py` — 文件敏感度分析，仅发送元数据（~144行）
- `anomaly.py` — 异常检测，规则引擎 + AI 增强双引擎 + 合并策略（~195行）
- `__init__.py` — 公共 API 导出（~12行）

## 依赖关系
- 本目录依赖：`openai` SDK、`src.core.detector`、`src.core.router`、`src.security.audit`、`src.watermarks.base`
- 被以下模块依赖：`src.core.embedder`（AI 强度建议）、`src.core.extractor`（异常检测）

## 设计原则
- **Opt-in**：`ai.enabled: false` 为默认，显式启用才调用 API
- **Graceful degradation**：AI 不可用时返回安全默认值，异常不阻断主流程
- **不发送文件内容**：只传文件名/类型/大小等元数据
- **双引擎**：异常检测同时有规则引擎，AI 只是增强
- **安全下限**：AI 不允许降低规则引擎的风险判定（merge 策略取 max）
- **防 prompt injection**：所有外部输入经 _sanitize.py 清洗后才拼入提示词

## 代码审查记录
- 2026-04-05: Codex gpt-5.3-codex + Sonnet 4.6 双模型审查 → Opus 4.6 最终裁决
- 修复 13 项问题（1 critical + 6 high + 6 medium），全部回归测试通过
