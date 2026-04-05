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
│   ├── settings.yaml          # 全局配置（日志、AI、安全等）
│   └── watermark_rules.yaml   # 文件类型→水印算法路由规则
├── src/                       # 源代码（40 文件，~4,633 行）
│   ├── main.py                # CLI 入口 — Click group + 命令注册
│   ├── core/                  # 核心调度层（5 文件，~837 行）
│   │   ├── detector.py        # 文件类型检测（magic bytes + 扩展名双重验证）
│   │   ├── router.py          # 策略路由（类型→处理器，lru_cache）
│   │   ├── embedder.py        # 统一嵌入接口（AI 强度建议 + 自动验证 + 回滚）
│   │   ├── extractor.py       # 统一提取接口（AI 异常检测 + 审计日志）
│   │   └── verifier.py        # 水印验证接口（单文件 + 批量验证）
│   ├── watermarks/            # 水印处理器（16 文件，~1,951 行）
│   │   ├── base.py            # 抽象基类 + 数据结构
│   │   ├── payload_codec.py   # 载荷编解码（v2 加密 1024-bit）
│   │   ├── _bwm_constants.py  # blind-watermark 共享常量
│   │   ├── zwc_codec.py       # 零宽字符编解码器
│   │   ├── image_wm.py        # 图像盲水印（DWT-DCT-SVD）
│   │   ├── pdf_wm.py          # PDF 盲水印（渲染→噪声→DWT-DCT-SVD→重建）
│   │   ├── text_wm.py         # 纯文本水印（零宽字符）
│   │   ├── office_wm.py       # Office 水印调度器
│   │   ├── _docx_handler.py   # DOCX 格式处理器
│   │   ├── _xlsx_handler.py   # XLSX 格式处理器
│   │   ├── _pptx_handler.py   # PPTX 格式处理器
│   │   ├── audio_wm.py        # 音频盲水印（DWT-DCT-QIM）
│   │   ├── _audio_core.py     # 音频核心算法
│   │   ├── video_wm.py        # 视频盲水印（逐帧 DWT-DCT-SVD + 多数表决）
│   │   └── _video_core.py     # 视频帧处理 + ffmpeg 工具
│   ├── security/              # 安全模块（4 文件，~384 行）
│   │   ├── crypto.py          # AES-256-GCM 加密/解密
│   │   ├── key_manager.py     # 密钥生成/保存/加载（环境变量优先）
│   │   └── audit.py           # 结构化审计日志（loguru sink）+ AI 调用审计
│   ├── ai/                    # AI 集成模块（6 文件，~567 行）
│   │   ├── ai_types.py        # SensitivityResult + AnomalyResult 数据类
│   │   ├── _sanitize.py       # 输入清洗（防 prompt injection）
│   │   ├── deepseek_client.py # DeepSeek API 客户端（OpenAI 兼容，懒加载）
│   │   ├── sensitivity.py     # 文件敏感度分析 + 策略建议
│   │   └── anomaly.py         # 异常/攻击检测（规则引擎 + AI 双引擎）
│   └── cli/                   # CLI 模块（5 文件，~748 行）
│       ├── __init__.py        # 共享工具：颜色输出、结果格式化、强度解析
│       ├── scan.py            # 目录扫描：过滤可处理文件、按类别统计
│       ├── verify_cmd.py      # verify 命令：单文件 + 目录批量验证
│       ├── batch_cmd.py       # batch 命令：auto/semi/manual 三模式
│       └── _batch_helpers.py  # batch 辅助函数
├── tests/                     # 测试套件（25 文件，~3,413 行，233 用例，覆盖率 72%）
│   ├── conftest.py            # 共享 fixtures（程序化生成测试数据）
│   ├── test_e2e.py            # 端到端集成测试（12 用例）
│   └── ...                    # 24 个测试文件，覆盖全部模块
├── docs/                      # 文档
│   ├── research.md            # 盲水印技术研究资料
│   └── usage.md               # 使用指南（API + CLI + 配置 + FAQ）
└── tasks/                     # 开发管理
    ├── todo.md                # 任务追踪
    └── lessons.md             # 纠错经验记录（20+ 条）
```

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
| 测试文件 | 25 个 |
| 测试用例 | 233 个 |
| 通过率 | 100% |
| 整体覆盖率 | 72% |
| 核心模块覆盖率 | ≥80%（key_manager 100%, payload_codec 91%, zwc_codec 97%, base 96%, crypto 86%）|

## 代码规模

| 模块 | 文件数 | 行数 |
|------|--------|------|
| src/ 源代码 | 40 | 4,633 |
| tests/ 测试 | 25 | 3,413 |
| **合计** | **65** | **~8,046** |

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
| 测试 | pytest + pytest-cov |

## License

MIT License

---

> Built with Claude Code for enterprise document security
