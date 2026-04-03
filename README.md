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

| 文件类型 | 水印算法 | 说明 |
|----------|----------|------|
| JPG/PNG/BMP/TIFF/WebP | **DWT-DCT-SVD** | 频域盲水印，抗压缩/缩放/裁剪 |
| PDF | **图层水印 + 文本水印** | 渲染为图像嵌入 + 零宽字符双重保护 |
| DOCX/PPTX | **图片水印 + 文本水印** | 嵌入图片加水印 + 文本零宽字符 |
| XLSX | **元数据 + 文本水印** | 文档属性 + 零宽字符 |
| MP3/WAV/FLAC | **DWT-DCT 频域** | 利用心理声学掩蔽模型 |
| MP4/AVI/MKV | **逐帧 DWT-DCT-SVD** | 关键帧水印嵌入 |
| TXT/CSV/JSON/MD | **零宽字符** | 插入不可见 Unicode 字符 |

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

### 3. CLI 命令（Phase 7 开发中）

```bash
# 单文件嵌入
python -m src.main embed --input report.pdf --employee E001

# 批量嵌入整个目录
python -m src.main batch --dir ./documents --employee E001

# 提取水印
python -m src.main extract --input leaked_file.pdf
```

## 项目架构

```
watermark/
├── config/                # 配置文件
│   ├── settings.yaml      # 全局配置（日志、AI、安全等）
│   └── watermark_rules.yaml  # 文件类型→水印算法路由规则
├── src/
│   ├── core/              # 核心调度层
│   │   ├── detector.py    # 文件类型检测（双重验证）
│   │   ├── router.py      # 策略路由（类型→处理器）
│   │   ├── embedder.py    # 统一嵌入接口
│   │   └── extractor.py   # 统一提取接口
│   ├── watermarks/        # 水印处理器（策略模式）
│   │   ├── base.py        # 抽象基类
│   │   ├── image_wm.py    # 图像盲水印
│   │   ├── pdf_wm.py      # PDF 水印
│   │   └── ...            # 其他类型
│   ├── security/          # 安全模块
│   │   ├── crypto.py      # AES-256 加密
│   │   ├── key_manager.py # 密钥管理
│   │   └── audit.py       # 审计日志
│   └── ai/                # AI 集成
│       └── deepseek_client.py  # DeepSeek API
├── tests/                 # 测试
├── docs/                  # 技术文档
│   └── research.md        # 盲水印技术研究资料
└── tasks/                 # 开发管理
    ├── todo.md            # 任务追踪
    └── lessons.md         # 经验记录
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

### 安全链路

```
水印嵌入：
载荷JSON → AES-256加密 → BCH纠错编码 → 嵌入文件

水印提取：
从文件提取 → BCH纠错解码 → AES-256解密 → 载荷JSON
```

## 开发进度

| 阶段 | 内容 | 状态 |
|------|------|------|
| Phase 0 | 项目初始化、技术调研 | ✅ 完成 |
| Phase 1 | 核心框架（检测/路由/嵌入/提取） | ✅ 完成 |
| Phase 2 | 图像盲水印 MVP | 🔜 下一步 |
| Phase 3 | 安全模块（AES加密/密钥/审计） | 📋 计划中 |
| Phase 4 | PDF + Office 水印 | 📋 计划中 |
| Phase 5 | 音视频水印 | 📋 计划中 |
| Phase 6 | DeepSeek AI 集成 | 📋 计划中 |
| Phase 7 | CLI + 自动化 | 📋 计划中 |
| Phase 8 | 测试 + 文档 | 📋 计划中 |

## 技术栈

| 分类 | 技术 |
|------|------|
| 语言 | Python 3.10+ |
| 图像水印 | blind-watermark + invisible-watermark |
| PDF | PyMuPDF + pdf2image |
| Office | python-docx / openpyxl / python-pptx |
| 文本水印 | text-blind-watermark |
| AI 集成 | DeepSeek API (OpenAI 兼容) |
| 加密 | cryptography (AES-256) |
| 文件检测 | python-magic-bin + filetype |
| CLI | click |

## License

MIT License

---

> Built with ❤️ for enterprise document security
