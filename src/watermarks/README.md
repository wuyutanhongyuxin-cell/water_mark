# watermarks — 各文件类型水印处理器

## 用途
实现各种文件类型的盲水印嵌入与提取。每个处理器继承 `WatermarkBase` 抽象基类。

## 架构
```
WatermarkBase (base.py)          ← 抽象基类，定义 embed/extract/verify 接口
  ├── ImageWatermark             ← Phase 2: DWT-DCT-SVD 图像盲水印
  ├── PdfWatermark               ← Phase 4: PDF 图层+文本水印
  ├── OfficeWatermark            ← Phase 4: DOCX/XLSX/PPTX 水印
  ├── AudioWatermark             ← Phase 5: 音频 DWT-DCT 水印
  ├── VideoWatermark             ← Phase 5: 视频逐帧水印
  └── TextWatermark              ← Phase 4: 零宽字符文本水印
```

## 文件清单
- `base.py` — 抽象基类 + 数据结构（WatermarkPayload, EmbedResult, ExtractResult）（~197行）
- `image_wm.py` — 图像盲水印（待实现 Phase 2）
- `pdf_wm.py` — PDF 水印（待实现 Phase 4）
- `office_wm.py` — Office 文档水印（待实现 Phase 4）
- `audio_wm.py` — 音频水印（待实现 Phase 5）
- `video_wm.py` — 视频水印（待实现 Phase 5）
- `text_wm.py` — 文本水印（待实现 Phase 4）

## 依赖关系
- 本目录依赖：各种第三方水印库（blind-watermark, PyMuPDF, etc.）
- 被以下模块依赖：`src.core.router`、`src.core.embedder`、`src.core.extractor`

## 新增水印处理器 Checklist
1. 继承 `WatermarkBase`，实现 `embed()` / `extract()` / `supported_extensions()`
2. 在 `config/watermark_rules.yaml` 注册路由规则
3. 编写嵌入-提取往返测试
4. 测试鲁棒性（压缩、缩放、格式转换）
