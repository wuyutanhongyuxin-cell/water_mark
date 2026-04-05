# WatermarkForge — 开发任务追踪

## Phase 0: 项目初始化 ✅
- [x] 技术调研 — 盲水印/暗水印原理、算法、开源库
- [x] 编写研究资料文档 `docs/research.md`
- [x] 编写项目规范 `CLAUDE.md`
- [x] 创建项目目录结构
- [x] 初始化 Git 仓库
- [x] 创建 `.env.example` + `.gitignore`
- [x] 编写 `requirements.txt`

## Phase 1: 核心框架 ✅ (代码审查后修复)
- [x] `src/watermarks/base.py` — 水印处理器抽象基类（198行）
- [x] `src/core/detector.py` — 文件类型检测 + OOXML/ZIP 特判 + MIME 清洗（195行）
- [x] `config/settings.yaml` — 全局配置（42行）
- [x] `config/watermark_rules.yaml` — 路由规则 + unknown 层级修复（74行）
- [x] `src/core/router.py` — 策略路由 + 白名单 + lru_cache（173行）
- [x] `src/core/embedder.py` — 统一嵌入 + 安全前置检查 + fail-closed 验证（179行）
- [x] `src/core/extractor.py` — 统一提取 + 错误模型统一（108行）
- [x] GPT-5.4 + Sonnet 4.6 双模型代码审查 → Opus 4.6 最终裁决
- [x] 13 项修复自检 + 5 项集成测试全部通过

## Phase 2: 图像水印（MVP）✅
- [x] `src/watermarks/image_wm.py` — DWT-DCT-SVD 图像盲水印（182行）
- [x] 固定 512-bit 编码方案（无需 sidecar 文件）
- [x] 嵌入-提取往返测试（PNG/BMP/中文ID 通过）
- [x] 鲁棒性测试：JPEG Q≥80 通过，缩放 0.5x~2.0x 全通过
- [x] PSNR 质量评估：LOW=44dB, MEDIUM=37dB, HIGH=33dB
- [x] 统一 API 集成测试 5/5 通过（embedder→auto_verify→extractor）

## Phase 3: 安全模块 + 中文路径修复 ✅
- [x] 修复 `src/core/detector.py` — magic.from_file→from_buffer 中文路径兼容
- [x] `src/security/crypto.py` — AES-256-GCM 加密/解密（~85行）
- [x] `src/security/key_manager.py` — 密钥管理：环境变量/文件/自动生成（~105行）
- [x] `src/security/audit.py` — 结构化审计日志 loguru sink（~105行）
- [x] `src/watermarks/image_wm.py` — v2 加密格式 1024-bit，兼容 v1 回退
- [x] `src/core/embedder.py` + `extractor.py` — 审计日志集成
- [x] `src/core/verifier.py` — 独立验证接口 + 批量验证（~110行）
- [x] 端到端验证：中文路径 + 加密嵌入 + 提取 + 验证 + 审计日志
- [x] image_wm.py 拆分 payload_codec.py（246→139+126 行）
- [x] cv2 中文路径修复：imdecode/imencode + embed_img 参数

## Phase 4: PDF + Office + Text 水印 ✅
- [x] `src/watermarks/zwc_codec.py` — 零宽字符编解码器，text_wm/office_wm 共用（~93行）
- [x] `src/watermarks/text_wm.py` — 纯文本零宽字符水印 TXT/CSV/JSON/MD（~124行）
- [x] `src/watermarks/pdf_wm.py` — PDF 渲染→噪声→DWT-DCT-SVD→重建（~197行）
- [x] `src/watermarks/office_wm.py` — Office 水印调度器（~106行）
- [x] `src/watermarks/_docx_handler.py` — DOCX 格式处理（~76行）
- [x] `src/watermarks/_xlsx_handler.py` — XLSX 格式处理（~81行）
- [x] `src/watermarks/_pptx_handler.py` — PPTX 格式处理（~88行）
- [x] 修复 `detector.py` OOXML 特判：application/octet-stream 也触发覆盖
- [x] PDF 纯白页面频域不足问题：嵌入前加微弱高斯噪声（sigma=3）
- [x] 端到端集成测试 8/8 通过（TXT/CSV/JSON/MD/DOCX/XLSX/PPTX/PDF）

## Phase 5: 音视频水印 ✅ (代码审查后修复)
- [x] `src/watermarks/_audio_core.py` — 音频核心算法 DWT-DCT-QIM（~157行）
- [x] `src/watermarks/audio_wm.py` — 音频盲水印处理器 WAV/FLAC（~192行）
- [x] `src/watermarks/_video_core.py` — 视频帧处理 + ffmpeg 工具（~123行）
- [x] `src/watermarks/video_wm.py` — 视频盲水印逐帧嵌入 + 多数表决（~197行）
- [x] 新增依赖：scipy + soundfile
- [x] 修复 detector.py 添加 `audio/x-flac` MIME 变体
- [x] OGG Vorbis 有损格式排除（与 MP3 同理）
- [x] FFV1 无损中间编码（解决 MJPG 有损破坏水印问题）
- [x] E2E 集成测试：WAV/FLAC/AVI 3/3 通过（embedder API + 自动验证 + 审计日志）
- [x] Codex gpt-5.3-codex + Sonnet 4.6 双模型代码审查 → Opus 4.6 最终裁决
- [x] 15 项修复：YAML 配置对齐、DRY 常量提取、边界防护、资源清理、日志改善
- [x] 审查后 E2E 回归测试 6/6 通过（图像+音频+视频+API 集成）

## Phase 6: DeepSeek AI 集成 ✅ (代码审查后修复)
- [x] `src/ai/ai_types.py` — SensitivityResult + AnomalyResult 数据类（~48行）
- [x] `src/ai/_sanitize.py` — 共享输入清洗工具，防 prompt injection（~25行）
- [x] `src/ai/deepseek_client.py` — API 客户端，懒加载+审计（~143行）
- [x] `src/ai/sensitivity.py` — 文件敏感度分析+策略建议，仅发元数据（~144行）
- [x] `src/ai/anomaly.py` — 异常/攻击检测，规则引擎+AI 双引擎+合并策略（~195行）
- [x] `src/security/audit.py` — 新增 `log_ai_call()` 审计 + 初始化竞态修复（~142行）
- [x] `src/core/embedder.py` — AI 强度建议 hook（仅升级不降级）（~200行）
- [x] `src/core/extractor.py` — AI 异常检测 hook + 文件大小检查（~135行）
- [x] `config/settings.yaml` — 新增 temperature 配置
- [x] Graceful degradation 验证：AI 禁用时全部返回安全默认值
- [x] 规则引擎测试：4 种 confidence 场景全部通过
- [x] JSON 解析测试：正常/非法值/非JSON/None 4 种场景通过
- [x] Codex gpt-5.3-codex + Sonnet 4.6 双模型代码审查 → Opus 4.6 最终裁决
- [x] 13 项修复：audit 竞态、AI 不降级安全、prompt injection 防护、bool 类型安全、异常隔离等
- [x] 审查后回归测试 6/6 通过（导入+清洗+规则引擎+合并+类型安全+降级）

## Phase 7: CLI + 自动化 ✅
- [x] `src/cli/__init__.py` — 共享 CLI 工具：颜色输出、结果格式化、强度解析（~150行）
- [x] `src/cli/scan.py` — 目录扫描：从 rules.yaml 动态读取扩展名、过滤隐藏文件（~100行）
- [x] `src/main.py` — Click group + embed/extract 命令（~110行）
- [x] `src/cli/verify_cmd.py` — verify 命令：单文件+目录批量验证+JSON输出（~120行）
- [x] `src/cli/batch_cmd.py` — batch 命令：auto/semi/manual 三模式+dry-run（~190行）
- [x] `src/cli/README.md` — CLI 模块文档
- [x] 零新依赖：Click 已在 requirements.txt
- [x] E2E 测试：embed→extract→verify 往返通过（文本文件）
- [x] batch auto 模式：2文件批量嵌入+验证全部通过
- [x] batch dry-run：文件列表+统计正确
- [x] 错误场景：不存在文件/错误ID/空目录 全部正确处理
- [x] 退出码：0=全成功, 1=部分失败, 2=全失败

## Phase 8: 测试 + 文档 ✅
- [x] pytest.ini + conftest.py 测试基础设施
- [x] 安全模块测试：test_crypto.py (10), test_key_manager.py (13)
- [x] 编解码测试：test_payload_codec.py (15), test_zwc_codec.py (9)
- [x] 基础类测试：test_base.py (14)
- [x] 检测+路由测试：test_detector.py (14), test_router.py (12)
- [x] 水印处理器测试：test_image_wm.py (6), test_text_wm.py (7), test_office_wm.py (7), test_pdf_wm.py (5), test_audio_wm.py (6), test_video_wm.py (6)
- [x] 核心 API 测试：test_embedder.py (11), test_extractor.py (8), test_verifier.py (6)
- [x] AI 模块测试：test_sanitize.py (12), test_ai_anomaly.py (17)
- [x] CLI 测试：test_cli_utils.py (16), test_cli_scan.py (13), test_cli_commands.py (10)
- [x] E2E 集成测试：test_e2e.py (12)
- [x] 性能基准测试：test_benchmark.py (4)
- [x] 使用文档：docs/usage.md + tests/README.md
- [x] **233 测试全部通过，覆盖率 72%**（核心模块 ≥80%）

---

## 进度记录
| 日期 | 完成内容 |
|------|----------|
| 2026-04-03 | Phase 0 技术调研完成，项目结构确定 |
| 2026-04-03 | Phase 1 核心框架完成：detector/router/embedder/extractor + 配置 + 10项测试通过 |
| 2026-04-03 | Phase 1 代码审查（GPT-5.4+Sonnet4.6+Opus4.6 三方审查）+ 13项修复 |
| 2026-04-03 | Phase 2 图像盲水印完成：DWT-DCT-SVD + 鲁棒性测试 + 集成测试 |
| 2026-04-04 | Phase 3 安全模块完成：AES-256-GCM + 密钥管理 + 审计日志 + 中文路径修复 |
| 2026-04-04 | Phase 4 完成：PDF/Office/Text 7 个新文件 + detector OOXML 修复 + E2E 8/8 通过 |
| 2026-04-04 | Phase 5 完成：音频 DWT-DCT-QIM + 视频逐帧 DWT-DCT-SVD + 多数表决，E2E WAV/FLAC/AVI 3/3 通过 |
| 2026-04-04 | Phase 5 代码审查：Codex+Sonnet 双审 → Opus 裁决，15 项修复 + E2E 6/6 回归通过 |
| 2026-04-04 | Phase 6 完成：DeepSeek AI 集成，4 个新文件 + 3 个修改，graceful degradation + 规则引擎 + JSON 解析全部测试通过 |
| 2026-04-05 | Phase 6 代码审查：Codex gpt-5.3-codex + Sonnet 4.6 双审 → Opus 4.6 裁决，13 项修复 + 回归 6/6 通过 |
| 2026-04-05 | Phase 7 完成：CLI 4 命令(embed/extract/verify/batch) + 3 模式(auto/semi/manual) + 目录扫描，6 个新文件，E2E 全部通过 |
| 2026-04-05 | Phase 8 完成：25 个测试文件 + 2 个文档，233 测试用例 100% 通过，覆盖率 72% |
