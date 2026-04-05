# tests/

## 用途
WatermarkForge 测试套件，覆盖所有核心模块的单元测试、集成测试和性能基准测试。

## 运行测试

```bash
# 运行全部测试（233 用例）
pytest

# 跳过慢测试（视频水印）
pytest -m "not slow"

# 跳过性能基准测试
pytest -m "not benchmark"

# 查看覆盖率报告
pytest --cov=src --cov-report=term-missing

# 运行单个测试文件
pytest tests/test_embedder.py -v
```

## 文件清单

### 基础设施
- `conftest.py` — 共享 fixtures：固定密钥、测试文件生成、autouse 重置（~216行）

### 安全模块测试
- `test_crypto.py` — AES-256-GCM 加密/解密、密钥验证、篡改检测（10 用例）
- `test_key_manager.py` — 密钥生成/保存/加载、环境变量优先级（13 用例）

### 编解码测试
- `test_payload_codec.py` — payload 编解码往返、1024-bit 长度、v1/v2 格式（15 用例）
- `test_zwc_codec.py` — 零宽字符编解码往返、标记检测、strip（9 用例）

### 基础类 + 检测 + 路由测试
- `test_base.py` — 枚举、数据类、抽象基类（14 用例）
- `test_detector.py` — 文件类型检测、OOXML 特判、边界情况（14 用例）
- `test_router.py` — 策略路由、规则加载、缓存（12 用例）

### 水印处理器测试
- `test_image_wm.py` — 图像嵌入/提取往返、PSNR 指标、强度对比（6 用例）
- `test_text_wm.py` — TXT/CSV/JSON/MD 往返、短文本拒绝（7 用例）
- `test_office_wm.py` — DOCX/XLSX/PPTX 往返、输出可打开（7 用例）
- `test_pdf_wm.py` — PDF 往返、完整性、空白 PDF 处理（5 用例）
- `test_audio_wm.py` — WAV 往返、SNR 指标、短音频拒绝（6 用例）
- `test_video_wm.py` — AVI 往返、帧指标、微小视频拒绝（6 用例，@slow）

### 核心 API 测试
- `test_embedder.py` — 统一嵌入 API、自动验证、回滚、输出路径安全（11 用例）
- `test_extractor.py` — 统一提取 API、验证 API（8 用例）
- `test_verifier.py` — 单文件验证、批量验证、错误隔离（6 用例）

### AI 模块测试
- `test_sanitize.py` — 输入清洗、prompt injection 防护（12 用例）
- `test_ai_anomaly.py` — 规则引擎、AI 合并策略、graceful degradation（17 用例）

### CLI 测试
- `test_cli_utils.py` — 强度解析、元数据解析、格式化输出（16 用例）
- `test_cli_scan.py` — 目录扫描、隐藏文件跳过、扩展名过滤（13 用例）
- `test_cli_commands.py` — Click CliRunner 命令测试（10 用例）

### 集成 + 性能测试
- `test_e2e.py` — 端到端：全文件类型 embed→extract→verify 链路（12 用例）
- `test_benchmark.py` — 性能基准：嵌入/提取耗时阈值（4 用例，@benchmark）

## 测试统计

| 指标 | 数值 |
|------|------|
| 测试文件 | 25 个 |
| 测试用例 | 233 个 |
| 通过率 | 100% |
| 整体覆盖率 | 72% |

## Fixture 策略
所有测试数据由 `conftest.py` 程序化生成（cv2、fitz、soundfile、python-docx 等），无需外部测试文件。

## autouse Fixtures
- `fixed_key` — 固定 WATERMARK_MASTER_KEY 确保确定性
- `disable_ai` — 移除 DEEPSEEK_API_KEY 禁用 AI 调用
- `reset_router_cache` — 清除 lru_cache 防止测试间污染
- `reset_audit_state` — 重置审计日志状态

## 依赖关系
- 本目录依赖：`src/` 全部模块
- 框架：pytest 7.4+ / pytest-cov 4.1+
