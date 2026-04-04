# cli/

## 用途
CLI 命令行界面模块，基于 Click 8.1+ 构建。提供 embed/extract/verify/batch 四个命令。

## 文件清单
- `__init__.py` — 共享工具：颜色输出、结果格式化、强度解析（~150行）
- `scan.py` — 目录扫描：过滤可处理文件、按类别统计（~100行）
- `verify_cmd.py` — verify 命令：单文件+目录批量验证（~120行）
- `batch_cmd.py` — batch 命令：auto/semi/manual 三模式批量嵌入（~198行）
- `_batch_helpers.py` — batch 辅助函数：嵌入、AI建议、选择解析（~110行）

## 依赖关系
- 本目录依赖：`src.core`（embedder/extractor/verifier/router）、`src.watermarks.base`、`src.ai`
- 被以下模块依赖：`src.main`（CLI 入口注册命令）

## 命令用法

```bash
# 嵌入水印
python -m src.main embed -i file.pdf -e E001

# 提取水印
python -m src.main extract -i file_wm.pdf [--json]

# 验证水印
python -m src.main verify -i file_wm.pdf [-e E001]
python -m src.main verify -i ./output/ -r

# 批量嵌入
python -m src.main batch -d ./docs/ -e E001 [-m auto|semi|manual] [--dry-run]
```
