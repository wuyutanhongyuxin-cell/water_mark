# WatermarkForge 🔒

**企业文档盲水印自动化系统** — 自动识别文件类型，嵌入最优盲水印，追踪文件泄露来源。

---

## 什么是盲水印？

盲水印（Blind Watermark）是一种**不可见**的数字水印技术：
- **嵌入时**：将追踪信息（员工ID、时间戳等）隐藏到文件中，肉眼完全不可见
- **提取时**：无需原始文件，直接从水印文件中提取隐藏信息
- **用途**：当文件泄露时，提取水印即可定位泄露源头

```
原始文件 ──→ [嵌入盲水印] ──→ 带水印文件（外观完全一样）
                                    │
                               文件泄露...
                                    │
                                    ▼
                            [提取盲水印] ──→ 员工ID: E001, 时间: 2026-04-03
```

## 核心特性

| 特性 | 说明 |
|------|------|
| **多格式支持** | 图片、PDF、Word/Excel/PPT、音频、视频、纯文本 |
| **自动检测** | magic bytes + 扩展名双重验证，自动匹配最优水印算法 |
| **安全加密** | 水印内容 AES-256 加密 + BCH 纠错编码 |
| **自动验证** | 嵌入后立即提取验证，确保水印正确 |
| **AI 增强** | DeepSeek API 分析文件敏感度，智能推荐水印策略 |
| **批量处理** | 一键扫描整个目录，自动批量加水印 |
| **审计追溯** | 每次操作记录完整日志，可追溯可审计 |
| **Web UI** | 浏览器操作界面，拖拽上传、实时进度、一键下载 |

## 支持的文件类型与算法

| 文件类型 | 水印算法 | 状态 |
|----------|----------|------|
| JPG/PNG/BMP/TIFF/WebP | **DWT-DCT-SVD** 频域盲水印 | ✅ 已实现 |
| PDF | **渲染→噪声→DWT-DCT-SVD→重建** | ✅ 已实现 |
| DOCX/XLSX/PPTX | **零宽字符** 嵌入文本 run/cell | ✅ 已实现 |
| TXT/CSV/JSON/MD | **零宽字符** 不可见 Unicode | ✅ 已实现 |
| WAV/FLAC | **DWT-DCT-QIM** 频域盲水印 | ✅ 已实现 |
| MP4/AVI/MKV/MOV | **逐帧 DWT-DCT-SVD** + 多数表决 | ✅ 已实现 |

## 快速开始

### 1. 安装

```bash
# 克隆仓库
git clone https://github.com/wuyutanhongyuxin-cell/water_mark.git
cd water_mark

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的 DeepSeek API Key（可选）
```

### 2. 基本使用

```python
from pathlib import Path
from src.core.embedder import embed_watermark
from src.core.extractor import extract_watermark
from src.watermarks.base import WatermarkPayload

# 嵌入水印
payload = WatermarkPayload(employee_id="E001")
result = embed_watermark(
    input_path=Path("confidential.pdf"),
    payload=payload,
)
print(f"嵌入结果: {result.success}, 输出: {result.output_path}")

# 提取水印（泄露追查时使用）
extracted = extract_watermark(Path("leaked_file.pdf"))
if extracted.success:
    print(f"泄露源: 员工 {extracted.payload.employee_id}")
    print(f"嵌入时间: {extracted.payload.timestamp}")
```

### 3. CLI 命令

```bash
# 单文件嵌入
python -m src.main embed -i report.pdf -e E001

# 提取水印
python -m src.main extract -i leaked_file.pdf

# 验证水印
python -m src.main verify -i file_wm.pdf -e E001

# 批量嵌入整个目录（auto/semi/manual 三模式）
python -m src.main batch -d ./documents -e E001 -m auto

# 批量验证目录
python -m src.main verify -i ./output/ -r

# 批量嵌入预览（不实际执行）
python -m src.main batch -d ./documents -e E001 --dry-run
```

## 项目架构

```
watermark/
├── config/                    # 配置文件
│   ├── settings.yaml          # 全局配置（日志、AI、安全、Web 等）
│   └── watermark_rules.yaml   # 文件类型→水印算法路由规则
├── src/                       # 源代码（57 文件，~5,977 行）
│   ├── main.py                # CLI 入口 — Click group + 命令注册
│   ├── core/                  # 核心调度层（5 文件，~837 行）
│   ├── watermarks/            # 水印处理器（16 文件，~1,951 行）
│   ├── security/              # 安全模块（4 文件，~384 行）
│   ├── ai/                    # AI 集成模块（6 文件，~567 行）
│   ├── cli/                   # CLI 模块（5 文件，~748 行）
│   └── web/                   # Web UI 模块（17 文件，~1,344 行）
│       ├── app.py             # FastAPI 应用工厂 + 生命周期
│       ├── schemas.py         # Pydantic v2 请求/响应模型
│       ├── dependencies.py    # 文件校验、上传保存、路径清洗
│       ├── routes/            # 路由层（6 文件）
│       │   ├── pages.py       # 页面渲染（嵌入/提取/验证/历史）
│       │   ├── api_embed.py   # 嵌入 API（单文件/批量/下载）
│       │   ├── api_extract.py # 提取 API
│       │   ├── api_verify.py  # 验证 API（单文件/批量）
│       │   └── api_tasks.py   # 任务状态/SSE/历史/配置
│       └── services/          # 业务逻辑层（4 文件）
│           ├── task_manager.py # 任务队列 + SSE 事件分发
│           ├── embed_service.py # 嵌入业务
│           ├── extract_service.py # 提取/验证业务
│           └── cleanup.py     # 临时文件清理守护线程
├── templates/                 # Jinja2 HTML 模板（9 文件）
├── static/                    # 静态资源 CSS/JS（7 文件）
├── tests/                     # 测试套件（27 文件，~3,870 行，264 用例）
├── docs/                      # 文档
└── tasks/                     # 开发管理
```

## Web UI 使用教程（浏览器操作）

> 不需要懂命令行！打开浏览器就能用，拖拽文件即可完成水印操作。

### 第一步：启动 Web 服务

```bash
# 进入项目目录
cd water_mark

# 安装依赖（只需要第一次）
pip install -r requirements.txt

# 启动 Web 服务
python -m src.web
```

看到下面这行就说明启动成功了：
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

然后打开浏览器，访问 **http://localhost:8000**

### 第二步：嵌入水印（给文件加水印）

1. 打开浏览器，进入 http://localhost:8000（自动跳转到嵌入页面）
2. **拖拽文件**到虚线框区域（或点击选择文件），支持同时多个文件
3. 填写 **员工 ID**（必填，比如 `E001` 或 `zhangsan`）
4. 选择 **嵌入强度**：
   - 低强度：视觉影响最小，适合高质量图片
   - 中强度（推荐）：平衡质量与鲁棒性
   - 高强度：最高鲁棒性，可能轻微影响质量
5. 点击 **"开始嵌入"** 按钮
6. 等待进度条走完（实时显示处理进度）
7. 处理完成后点击 **"下载文件"** 保存带水印的文件

```
支持的文件格式：
  图片: JPG, PNG, BMP, TIFF, WebP
  文档: PDF, DOCX, XLSX, PPTX
  文本: TXT, CSV, JSON, MD
  音频: WAV, FLAC
  视频: MP4, AVI, MKV, MOV
```

### 第三步：提取水印（查看文件里藏了什么）

1. 点击顶部导航 **"提取水印"**
2. 拖拽或选择一个带水印的文件
3. 点击 **"提取水印"** 按钮
4. 页面会显示：
   - **员工 ID**（大号字体，一眼看到是谁的水印）
   - **嵌入时间**（什么时候加的水印）
   - **置信度**（提取的可信程度，绿色=高，黄色=中，红色=低）

### 第四步：验证水印（批量检查一批文件）

1. 点击顶部导航 **"验证水印"**
2. 拖拽多个文件���上传区
3. （可选）填写 **预期员工 ID**，用来检查是否匹配
4. 点击 **"开始验证"**
5. 结果表格显示每个文件的状态：
   - ✓ 绿色 = 验证通过
   - ✗ 红色 = 验证失败或不匹配

### 第五步：查看操作历史

1. 点击顶部导航 **"操作历史"**
2. 看到所有嵌入/提取/验证的操作记录
3. 可以按操作类型筛选（嵌入/提取/验证）

### Web API（给开发者用）

如果你需要通过程序调用，Web 服务同时提供 REST API：

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/embed` | 单文件嵌入水印 |
| POST | `/api/embed/batch` | 批量嵌入 |
| GET | `/api/embed/{task_id}/download` | 下载水印文件 |
| POST | `/api/extract` | 提取水印 |
| POST | `/api/verify` | 单文件验证 |
| POST | `/api/verify/batch` | 批量验证 |
| GET | `/api/tasks/{task_id}/events` | SSE 实时进度 |
| GET | `/api/config` | 查看支持的文件类型 |

API 文档：启动服务后访问 http://localhost:8000/docs（Swagger UI）

---

## 技术原理

### DWT-DCT-SVD 图像盲水印（核心算法）

```
嵌入流程：
原图 → DWT(离散小波变换) → 选中频子带 → DCT(离散余弦变换) → SVD(奇异值分解)
  → 修改奇异值嵌入水印比特 → 逆SVD → 逆DCT → 逆DWT → 水印图

提取流程：
水印图 → DWT → DCT → SVD → 提取奇异值差异 → 恢复水印比特
```

**为什么选这个组合？**
- **DWT**：多分辨率分析，与人类视觉系统匹配，隐匿性好
- **DCT**：JPEG 压缩基于 DCT，天然抗 JPEG 压缩
- **SVD**：奇异值极其稳定，抗各种信号处理攻击

### DWT-DCT-QIM 音频盲水印

```
嵌入流程：
音频信号 → 1D Haar DWT → detail 系数分块 → DCT → QIM 量化调制嵌入 → IDCT → IDWT → 水印音频

提取流程：
水印音频 → 1D Haar DWT → detail 系数分块 → DCT → QIM 提取比特 → 水印载荷
```

- 仅支持无损格式（WAV/FLAC），有损格式会破坏水印
- 嵌入在左声道高频 detail 系数，SNR ~48dB（MEDIUM 强度）

### 视频逐帧水印 + 多数表决

```
嵌入流程：
视频 → 每 N 帧提取 → 帧级 DWT-DCT-SVD 嵌入 → FFV1 无损编码 → 合并音轨 → 输出

提取流程：
视频 → 每 N 帧提取 → 帧级 DWT-DCT-SVD 提取 → 多数表决投票 → 水印载荷
```

- FFV1 无损中间编码，保护帧间水印不被有损压缩破坏
- 多帧多数表决提高鲁棒性，ffmpeg 可用时自动保留音轨

### 安全链路

```
水印嵌入：
载荷JSON → AES-256-GCM 加密 → 1024-bit 编码 → 嵌入文件

水印提取：
从文件提取 → 1024-bit 解码 → AES-256-GCM 解密 → 载荷JSON
```

## 开发进度

| 阶段 | 内容 | 状态 |
|------|------|------|
| Phase 0 | 项目初始化、技术调研 | ✅ 完成 |
| Phase 1 | 核心框架（检测/路由/嵌入/提取）+ 三方代码审查 | ✅ 完成 |
| Phase 2 | 图像盲水印 MVP（DWT-DCT-SVD, PSNR≥37dB） | ✅ 完成 |
| Phase 3 | 安全模块（AES-256-GCM/密钥管理/审计日志） | ✅ 完成 |
| Phase 4 | PDF + Office + Text 水印（8 种格式，E2E 8/8 通过） | ✅ 完成 |
| Phase 5 | 音视频水印（DWT-DCT-QIM + 逐帧 DWT-DCT-SVD）+ 三方代码审查 | ✅ 完成 |
| Phase 6 | DeepSeek AI 集成（敏感度分析 + 异常检测 + 规则引擎）+ 三方代码审查 | ✅ 完成 |
| Phase 7 | CLI 命令行（embed/extract/verify/batch 四命令 + 三模式批量处理） | ✅ 完成 |
| Phase 8 | 测试套件（233 用例，覆盖率 72%）+ 使用文档 | ✅ 完成 |
| Phase 9 | Web UI（FastAPI + Tailwind + Alpine.js，4 页面 + 16 路由 + SSE 实时进度） | ✅ 完成 |

## 测试

```bash
# 运行全部测试
pytest

# 跳过慢测试（视频水印 + 性能基准）
pytest -m "not slow and not benchmark"

# 查看覆盖率报告
pytest --cov=src --cov-report=term-missing
```

| 指标 | 数值 |
|------|------|
| 测试文件 | 27 个 |
| 测试用例 | 264 个（含 31 个 Web UI 测试） |
| 通过率 | 100% |
| 整体覆盖率 | 72% |
| 核心模块覆盖率 | ≥80%（key_manager 100%, payload_codec 91%, zwc_codec 97%, base 96%, crypto 86%）|

## 代码规模

| 模块 | 文件数 | 行数 |
|------|--------|------|
| src/ 源代码 | 57 | 5,977 |
| templates/ 模板 | 9 | 1,000 |
| static/ 前端资源 | 7 | 901 |
| tests/ 测试 | 27 | 3,870 |
| **合计** | **100** | **~11,748** |

## 技术栈

| 分类 | 技术 |
|------|------|
| 语言 | Python 3.10+ |
| 图像水印 | blind-watermark (DWT-DCT-SVD) |
| PDF | PyMuPDF (渲染→DWT-DCT-SVD→重建) |
| Office | python-docx / openpyxl / python-pptx |
| 文本水印 | 自研零宽字符编码（zwc_codec） |
| 音频水印 | soundfile + scipy (DWT-DCT-QIM) |
| 视频水印 | opencv + blind-watermark + ffmpeg |
| AI 集成 | DeepSeek API (OpenAI 兼容) |
| 加密 | cryptography (AES-256-GCM) |
| 文件检测 | python-magic-bin + filetype |
| CLI | click |
| Web 框架 | FastAPI + Jinja2 |
| Web 服务器 | uvicorn |
| 前端 UI | Tailwind CSS + Alpine.js |
| 测试 | pytest + pytest-cov + httpx |

## License

MIT License

---

> Built with Claude Code for enterprise document security
