# watermarks — 各文件类型水印处理器

## 用途
实现各种文件类型的盲水印嵌入与提取。每个处理器继承 `WatermarkBase` 抽象基类。

## 架构
```
WatermarkBase (base.py)          ← 抽象基类，定义 embed/extract/verify 接口
  ├── ImageWatermark (image_wm)  ← ✅ Phase 2: DWT-DCT-SVD 图像盲水印
  ├── PdfWatermark               ← Phase 4: PDF 图层+文本水印
  ├── OfficeWatermark            ← Phase 4: DOCX/XLSX/PPTX 水印
  ├── AudioWatermark             ← Phase 5: 音频 DWT-DCT 水印
  ├── VideoWatermark             ← Phase 5: 视频逐帧水印
  └── TextWatermark              ← Phase 4: 零宽字符文本水印
```

## 文件清单
- `base.py` — 抽象基类 + 数据结构（WatermarkPayload, EmbedResult, ExtractResult）（~198行）
- `image_wm.py` — **图像盲水印** DWT-DCT-SVD，512-bit 固定编码，PSNR≥37dB（~182行）

## ImageWatermark 技术细节

### 算法
```
嵌入: 原图 → DWT → DCT → SVD → 修改奇异值 → 逆变换 → 水印图
提取: 水印图 → DWT → DCT → SVD → 读取奇异值差异 → 恢复比特
```

### 载荷编码
- 固定 64 字节 = 512 bits（JSON 压缩 + 0x00 填充）
- 提取时无需额外 metadata 文件

### 强度映射
| 级别 | d1/d2 | PSNR | 适用场景 |
|------|-------|------|---------|
| LOW | 15/8 | ~44dB | 高质量要求，低攻击风险 |
| MEDIUM | 36/20 | ~37dB | 平衡（默认） |
| HIGH | 64/36 | ~33dB | 高攻击风险，需最大鲁棒性 |

### 鲁棒性（MEDIUM 强度）
| 攻击 | 结果 |
|------|------|
| JPEG Q≥80 | ✅ 通过 |
| 缩放 0.5x~2.0x | ✅ 通过 |
| PNG 无损 | ✅ 通过 |
| BMP 无损 | ✅ 通过 |
| JPEG Q<60 | ❌ 失败 |

## 依赖关系
- 本目录依赖：blind-watermark, opencv-python-headless, numpy
- 被以下模块依赖：`src.core.router`、`src.core.embedder`、`src.core.extractor`

## 新增水印处理器 Checklist
1. 继承 `WatermarkBase`，实现 `embed()` / `extract()` / `supported_extensions()`
2. 在 `config/watermark_rules.yaml` 注册路由规则
3. 编写嵌入-提取往返测试
4. 测试鲁棒性（压缩、缩放、格式转换）
