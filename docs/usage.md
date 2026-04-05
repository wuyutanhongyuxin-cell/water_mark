# WatermarkForge 使用指南

## 目录
1. [快速开始](#快速开始)
2. [Python API](#python-api)
3. [CLI 命令参考](#cli-命令参考)
4. [配置说明](#配置说明)
5. [常见问题排查](#常见问题排查)

---

## 快速开始

### 安装

```bash
# 克隆项目
git clone <repo-url>
cd watermark

# 安装依赖
pip install -r requirements.txt

# 配置密钥（必须，64 位十六进制字符串）
# 在项目根目录创建 .env 文件
echo "WATERMARK_MASTER_KEY=your_64_char_hex_key_here" > .env
```

### 基本用法

```bash
# 嵌入水印到图片
python -m src.main embed -i photo.png -e E001

# 从文件中提取水印
python -m src.main extract -i photo_wm.png

# 验证文件中的水印
python -m src.main verify -i photo_wm.png -e E001

# 批量处理目录
python -m src.main batch -d ./documents/ -e E001
```

---

## Python API

### 嵌入水印

`embed_watermark` 是嵌入水印的统一入口，自动识别文件类型并选择最优算法。

```python
from pathlib import Path
from src.core.embedder import embed_watermark
from src.watermarks.base import WatermarkPayload, WatermarkStrength

# 构建水印载荷（employee_id 为必填项）
payload = WatermarkPayload(
    employee_id="E001",
    custom_data={"dept": "Finance", "level": "3"},
)

# 嵌入水印
result = embed_watermark(
    input_path=Path("report.pdf"),
    payload=payload,
    output_path=Path("report_wm.pdf"),    # 可选，不指定则自动生成
    strength=WatermarkStrength.MEDIUM,      # 可选，默认 MEDIUM
    auto_verify=True,                       # 可选，默认嵌入后自动验证
)

# 检查结果
if result.success:
    print(f"成功！输出文件: {result.output_path}")
    print(f"耗时: {result.elapsed_time:.2f}s")
else:
    print(f"失败: {result.message}")
```

**参数说明：**
| 参数 | 类型 | 说明 |
|------|------|------|
| `input_path` | `Path` | 输入文件路径（必填） |
| `payload` | `WatermarkPayload` | 水印载荷数据（必填） |
| `output_path` | `Path` | 输出文件路径（可选，默认自动生成） |
| `output_dir` | `Path` | 输出目录（可选，与 output_path 二选一） |
| `strength` | `WatermarkStrength` | 水印强度：LOW / MEDIUM / HIGH |
| `auto_verify` | `bool` | 嵌入后是否自动提取验证 |

### 提取水印

```python
from pathlib import Path
from src.core.extractor import extract_watermark, verify_watermark

# 提取水印
result = extract_watermark(Path("report_wm.pdf"))

if result.success:
    print(f"员工 ID: {result.payload.employee_id}")
    print(f"时间戳: {result.payload.timestamp}")
    print(f"置信度: {result.confidence:.2f}")
    if result.payload.custom_data:
        print(f"自定义数据: {result.payload.custom_data}")
else:
    print(f"提取失败: {result.message}")

# 快速验证（只比对 employee_id）
is_match = verify_watermark(Path("report_wm.pdf"), "E001")
print(f"验证结果: {'通过' if is_match else '不匹配'}")
```

### 验证水印

```python
from pathlib import Path
from src.core.verifier import verify_file, batch_verify

# 单文件验证
result = verify_file(
    Path("report_wm.pdf"),
    expected_employee_id="E001",    # 可选，不传则只检查水印是否存在
)
print(f"成功: {result.success}")
print(f"匹配: {result.matched}")
print(f"员工 ID: {result.employee_id}")

# 批量验证多个文件
results = batch_verify(
    [Path("file1.pdf"), Path("file2.docx"), Path("file3.png")],
    expected_employee_id="E001",
)
for r in results:
    status = "通过" if r.success and r.matched else "失败"
    print(f"{r.file_path.name}: {status} - {r.message}")
```

---

## CLI 命令参考

### embed — 嵌入水印

```bash
python -m src.main embed [选项]
```

| 选项 | 说明 |
|------|------|
| `-i, --input` | 输入文件路径（必填） |
| `-e, --employee` | 员工 ID（必填） |
| `-o, --output` | 输出文件路径 |
| `-d, --output-dir` | 输出目录 |
| `-s, --strength` | 水印强度：low / medium / high |
| `--no-verify` | 跳过嵌入后验证 |
| `-c, --custom` | 自定义元数据 key=value（可重复） |

```bash
# 示例：嵌入带自定义数据的水印
python -m src.main embed -i doc.pdf -e E001 -s high -c dept=Finance -c level=3

# 指定输出目录
python -m src.main embed -i photo.png -e E001 -d ./output/
```

### extract — 提取水印

```bash
python -m src.main extract [选项]
```

| 选项 | 说明 |
|------|------|
| `-i, --input` | 已加水印的文件路径（必填） |
| `-s, --strength` | 水印强度 |
| `--json` | 以 JSON 格式输出 |

```bash
# 示例：提取并以 JSON 输出
python -m src.main extract -i doc_wm.pdf --json
```

### verify — 验证水印

```bash
python -m src.main verify [选项]
```

| 选项 | 说明 |
|------|------|
| `-i, --input` | 文件或目录路径（必填） |
| `-e, --employee` | 预期员工 ID（可选） |
| `-s, --strength` | 水印强度 |
| `-r, --recursive` | 递归扫描目录 |
| `--json` | JSON 格式输出 |

```bash
# 单文件验证
python -m src.main verify -i doc_wm.pdf -e E001

# 目录批量验证
python -m src.main verify -i ./output/ -e E001 -r
```

### batch — 批量嵌入

```bash
python -m src.main batch [选项]
```

| 选项 | 说明 |
|------|------|
| `-d, --dir` | 待处理目录（必填） |
| `-e, --employee` | 员工 ID（必填） |
| `-o, --output-dir` | 输出目录 |
| `-s, --strength` | 水印强度 |
| `-m, --mode` | 处理模式：auto / semi / manual |
| `--recursive / --no-recursive` | 递归扫描 |
| `--skip-errors / --no-skip-errors` | 遇错是否跳过 |
| `--dry-run` | 仅列出文件，不实际处理 |
| `--no-verify` | 跳过嵌入后验证 |

```bash
# 全自动批量处理
python -m src.main batch -d ./documents/ -e E001 -o ./output/

# 预览模式（不实际处理）
python -m src.main batch -d ./documents/ -e E001 --dry-run

# 半自动模式（逐文件确认）
python -m src.main batch -d ./documents/ -e E001 -m semi --skip-errors
```

---

## 配置说明

### settings.yaml

全局配置文件，位于 `config/settings.yaml`。

```yaml
# 水印默认参数
watermark:
  default_strength: "medium"    # 默认强度：low / medium / high
  auto_verify: true             # 嵌入后自动验证
  max_file_size_mb: 500         # 单文件最大处理大小

# 输出设置
output:
  directory: "output"           # 默认输出目录
  naming: "{stem}_wm{ext}"     # 命名模板，{stem}=文件名，{ext}=扩展名
  overwrite: false              # 是否覆盖已有文件

# 批量处理
batch:
  max_workers: 4                # 并行线程数
  skip_errors: false            # 遇错跳过
  recursive: true               # 递归扫描子目录
```

### watermark_rules.yaml

水印策略路由规则，位于 `config/watermark_rules.yaml`。定义了每种文件类型使用的处理器和算法参数。

支持的文件类型：
- **图像**：JPG、PNG、BMP、TIFF、WebP → DWT-DCT-SVD 算法
- **PDF**：图层水印 + 文本水印
- **Office**：DOCX、XLSX、PPTX → 图片/元数据 + 零宽字符
- **音频**：WAV、FLAC → DWT-DCT-QIM 算法
- **视频**：MP4、AVI、MKV、MOV → 逐帧 DWT-DCT-SVD
- **文本**：TXT、CSV、JSON、MD → 零宽字符

---

## 常见问题排查

### 1. "WATERMARK_MASTER_KEY not set" 错误

**原因**：未配置主密钥环境变量。

**解决**：在项目根目录创建 `.env` 文件，写入 64 位十六进制密钥：
```
WATERMARK_MASTER_KEY=aabbccdd...（64个十六进制字符）
```

### 2. "Output path must differ from input path" 错误

**原因**：输出文件路径与输入文件相同，为防止回滚时误删原文件而拒绝处理。

**解决**：指定不同的输出路径或使用 `-d` 指定输出目录。

### 3. "Routing failed" / "No processor found" 错误

**原因**：文件类型不在支持列表中，或文件扩展名与实际内容不匹配。

**解决**：
- 确认文件扩展名正确（如 `.jpg` 而非 `.jpeg_backup`）
- 使用 `--dry-run` 查看哪些文件会被处理

### 4. "Verification failed after embedding" 错误

**原因**：嵌入后的自动验证未通过，水印可能未正确写入。

**解决**：
- 尝试使用更高的强度：`-s high`
- 检查文件是否损坏或过小
- 图像至少需要 100x100 像素

### 5. "File too large" 错误

**原因**：文件超过配置的最大处理大小（默认 500MB）。

**解决**：修改 `config/settings.yaml` 中的 `max_file_size_mb` 参数。

### 6. 提取时置信度很低（confidence < 0.5）

**原因**：文件可能经过压缩、缩放或格式转换，水印信号衰减。

**解决**：
- 嵌入时使用更高强度：`-s high`
- 避免对已加水印文件进行有损操作
- 确保提取时使用与嵌入时相同的强度参数
