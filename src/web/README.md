# web — Web UI 模块

## 用途
基于 FastAPI 的 Web 界面，提供水印嵌入、提取、验证的浏览器操作界面和 REST API。

## 文件清单
- `__init__.py` — 模块入口，版本声明（~13行）
- `__main__.py` — 支持 `python -m src.web` 启动（~18行）
- `app.py` — FastAPI 应用工厂，生命周期管理（~80行）
- `schemas.py` — Pydantic v2 请求/响应数据模型（~115行）
- `dependencies.py` — 公共依赖：文件校验、路径管理（~115行）
- `routes/__init__.py` — 路由注册中心（~25行）
- `routes/pages.py` — HTML 页面路由（~45行）
- `routes/api_embed.py` — 嵌入 API：单文件/批量/下载（~120行）
- `routes/api_extract.py` — 提取 API（~50行）
- `routes/api_verify.py` — 验证 API：单文件/批量（~90行）
- `routes/api_tasks.py` — 任务状态/SSE/历史/配置 API（~110行）
- `services/__init__.py` — 服务层入口（~5行）
- `services/task_manager.py` — 任务管理器：状态追踪、SSE、历史（~185行）
- `services/embed_service.py` — 嵌入业务逻辑（~100行）
- `services/extract_service.py` — 提取/验证业务逻辑（~120行）

## API 端点一览
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/embed | 单文件嵌入水印 |
| POST | /api/embed/batch | 批量嵌入水印 |
| GET | /api/embed/{task_id}/download | 下载水印文件 |
| POST | /api/extract | 提取水印 |
| POST | /api/verify | 单文件验证 |
| POST | /api/verify/batch | 批量验证 |
| GET | /api/tasks/{task_id} | 查询任务状态 |
| GET | /api/tasks/{task_id}/events | SSE 事件流 |
| GET | /api/tasks/history | 操作历史 |
| GET | /api/config | 系统配置 |

## 依赖关系
- 本模块依赖：`src.core`（embedder, extractor, verifier）、`src.watermarks.base`
- 被以下模块依赖：无（顶层入口模块）
- 外部依赖：`fastapi`, `uvicorn`, `pydantic`, `jinja2`, `python-multipart`
