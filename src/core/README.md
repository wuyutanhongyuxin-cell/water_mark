# core — 核心逻辑模块

## 用途
水印系统的核心调度层：文件检测、策略路由、统一嵌入/提取接口。

## 数据流
```
文件输入
  │
  ▼
detector.py ──── 检测文件类型（magic bytes + 扩展名双重验证）
  │
  ▼
router.py ────── 匹配水印策略（查 watermark_rules.yaml）
  │
  ▼
embedder.py ──── 嵌入水印（调用处理器 → 自动验证 → 审计日志）
extractor.py ─── 提取水印（调用处理器 → 返回载荷）
verifier.py ──── 独立验证（提取 + 比对 → 审计日志）
```

## 文件清单
- `detector.py` — 文件类型检测，双重验证，中文路径兼容（~200行）
- `router.py` — 策略路由，动态加载处理器（~172行）
- `embedder.py` — 统一嵌入接口，含自动验证、回滚和审计（~192行）
- `extractor.py` — 统一提取接口，含审计日志（~110行）
- `verifier.py` — 独立验证接口，支持单文件和批量验证（~130行）

## 依赖关系
- 本目录依赖：`src.watermarks.base`、`src.security`、`config/`
- 被以下模块依赖：`src.main`（CLI 入口）、`tests/`

## 核心 API
```python
from src.core.embedder import embed_watermark
from src.core.extractor import extract_watermark
from src.core.verifier import verify_file, batch_verify
from src.core.detector import detect_file_type
from src.core.router import route_file
```
