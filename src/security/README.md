# security — 安全模块

## 用途
AES-256-GCM 水印载荷加密、密钥管理、审计日志。

## 文件清单
- `crypto.py` — AES-256-GCM 加密/解密（~91行）
- `key_manager.py` — 密钥生成/保存/加载，支持环境变量（~140行）
- `audit.py` — 结构化审计日志（loguru sink）+ AI 调用审计（~142行）
- `__init__.py` — 公共 API 导出（~12行）

## 依赖关系
- 本目录依赖：`cryptography` 库、`loguru`、`src.core.router`（audit 读取配置）
- 被以下模块依赖：`src.watermarks.image_wm`、`src.core.embedder`、`src.core.extractor`、`src.core.verifier`、`src.ai.deepseek_client`
