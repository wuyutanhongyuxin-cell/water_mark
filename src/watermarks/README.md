# watermarks — 各文件类型水印处理器

## 用途
实现各种文件类型的盲水印嵌入与提取。每个处理器继承 `WatermarkBase` 抽象基类。

## 架构
```
WatermarkBase (base.py)          ← 抽象基类，定义 embed/extract/verify 接口
  ├── ImageWatermark (image_wm)  ← ✅ Phase 2: DWT-DCT-SVD 图像盲水印
  ├── PdfWatermark (pdf_wm)      ← ✅ Phase 4: PDF 渲染→DWT-DCT-SVD→重建
  ├── OfficeWatermark (office_wm)← ✅ Phase 4: DOCX/XLSX/PPTX 零宽字符水印
  ├── TextWatermark (text_wm)    ← ✅ Phase 4: TXT/CSV/JSON/MD 零宽字符水印
  ├── AudioWatermark             ← Phase 5: 音频 DWT-DCT 水印
  └── VideoWatermark             ← Phase 5: 视频逐帧水印
```

## 文件清单

### 核心模块
- `base.py` — 抽象基类 + 数据结构（WatermarkPayload, EmbedResult, ExtractResult）（~200行）
- `payload_codec.py` — 水印载荷编解码器，v1/v2 加密格式处理（~135行）
- `zwc_codec.py` — **零宽字符编解码器**，text_wm 和 office_wm 共用（~93行）

### 处理器
- `image_wm.py` — **图像盲水印** DWT-DCT-SVD，v2 加密 1024-bit 格式（~172行）
- `text_wm.py` — **纯文本水印** 零宽字符，支持 TXT/CSV/JSON/MD（~124行）
- `pdf_wm.py` — **PDF 盲水印** 渲染→噪声→DWT-DCT-SVD→重建（~197行）
- `office_wm.py` — **Office 水印调度器** 分发到 DOCX/XLSX/PPTX handler（~106行）

### Office 格式处理器（内部模块）
- `_docx_handler.py` — DOCX 格式读写，修改 run.text 保持格式（~76行）
- `_xlsx_handler.py` — XLSX 格式读写，修改字符串 cell（~81行）
- `_pptx_handler.py` — PPTX 格式读写，遍历 slide→shape→run（~88行）

## 技术细节

### 载荷编码（v2 加密格式，所有处理器共用）
- 固定 128 字节 = 1024 bits
- 格式: `[version 1B][key_id 1B][encrypted_len 1B][AES-GCM 密文][padding]`
- AES-256-GCM 加密，密钥由 key_manager 管理

### 零宽字符编码（text_wm / office_wm）
- 协议: `[ZWJ 开始标记][1024 个 ZWC 字符][WJ 结束标记]`
- ZWC_BIT_0 = U+200B, ZWC_BIT_1 = U+200C
- 肉眼完全不可见，程序精确提取

### PDF 水印特殊处理
- 输出为纯图像 PDF（丢失文本可选性，最大化鲁棒性）
- 嵌入前添加微弱高斯噪声（sigma=3，PSNR≈40dB）提供频域纹理
- 固定 200 DPI 渲染，嵌入/提取必须一致

## 依赖关系
- 本目录依赖：blind-watermark, opencv-python-headless, numpy, PyMuPDF, python-docx, openpyxl, python-pptx, `src.security`
- 被以下模块依赖：`src.core.router`、`src.core.embedder`、`src.core.extractor`

## 新增水印处理器 Checklist
1. 继承 `WatermarkBase`，实现 `embed()` / `extract()` / `supported_extensions()`
2. 在 `config/watermark_rules.yaml` 注册路由规则
3. 编写嵌入-提取往返测试
4. 测试鲁棒性（压缩、缩放、格式转换）
