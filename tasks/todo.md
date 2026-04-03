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

## Phase 3: 安全模块
- [ ] `src/security/crypto.py` — AES-256 水印加密
- [ ] `src/security/key_manager.py` — 密钥管理
- [ ] `src/security/audit.py` — 审计日志
- [ ] `src/core/verifier.py` — 嵌入后自动校验

## Phase 4: PDF + Office 水印
- [ ] `src/watermarks/pdf_wm.py` — PDF 盲水印
- [ ] `src/watermarks/office_wm.py` — DOCX/XLSX/PPTX 水印
- [ ] `src/watermarks/text_wm.py` — 纯文本零宽字符水印

## Phase 5: 音视频水印
- [ ] `src/watermarks/audio_wm.py` — 音频 DWT-DCT 水印
- [ ] `src/watermarks/video_wm.py` — 视频逐帧水印

## Phase 6: DeepSeek AI 集成
- [ ] `src/ai/deepseek_client.py` — API 客户端
- [ ] 文件敏感度分析功能
- [ ] 智能水印策略建议
- [ ] 异常/攻击检测

## Phase 7: CLI + 自动化
- [ ] `src/main.py` — CLI 命令（embed / extract / verify / batch）
- [ ] 批量处理：扫描目录自动加水印
- [ ] 半自动模式：DeepSeek 建议 + 人工确认
- [ ] 全自动模式：按规则自动处理

## Phase 8: 测试 + 文档
- [ ] 所有模块的单元测试
- [ ] 端到端集成测试
- [ ] 性能基准测试
- [ ] 使用文档

---

## 进度记录
| 日期 | 完成内容 |
|------|----------|
| 2026-04-03 | Phase 0 技术调研完成，项目结构确定 |
| 2026-04-03 | Phase 1 核心框架完成：detector/router/embedder/extractor + 配置 + 10项测试通过 |
| 2026-04-03 | Phase 1 代码审查（GPT-5.4+Sonnet4.6+Opus4.6 三方审查）+ 13项修复 |
| 2026-04-03 | Phase 2 图像盲水印完成：DWT-DCT-SVD + 鲁棒性测试 + 集成测试 |
