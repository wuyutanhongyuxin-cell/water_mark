# CLAUDE.md — 企业文档盲水印自动化系统

> 把这个文件放在项目根目录。Claude Code 每次启动自动读取。
> 下方 [项目专属区域] 根据具体项目填写，其余部分所有项目通用。

---

## [项目专属区域] — 每个项目必须填写

### 项目名称
**WatermarkForge** — 企业文档盲水印自动化系统

### 一句话描述
自动识别文件类型并嵌入最优盲水印的企业级工具，用于追踪发给员工的文件泄露来源。

### 技术栈

| 分类 | 技术选型 | 说明 |
|------|----------|------|
| 语言 | **Python 3.10+** | 生态最完善 |
| 图像水印 | `blind-watermark` + `invisible-watermark` | DWT-DCT-SVD + RivaGAN |
| PDF 处理 | `PyMuPDF (fitz)` + `pdf2image` | 渲染/重建 PDF |
| Office 处理 | `python-docx` / `openpyxl` / `python-pptx` | DOCX/XLSX/PPTX |
| 文本水印 | `text_blind_watermark` | 零宽字符嵌入 |
| 音频水印 | `audiowmark` 或自研 DWT-DCT | WAV/MP3/FLAC |
| 视频水印 | `FFmpeg` + 逐帧图像水印 | MP4/AVI/MKV |
| AI 集成 | **DeepSeek API** (OpenAI 兼容) | 智能分析与策略建议 |
| 加密 | `cryptography` (Fernet/AES) | 水印内容加密 |
| 文件检测 | `python-magic-bin` + `filetype` + 扩展名 | Windows 兼容的双重验证 |
| 配置 | YAML (`PyYAML`) | 可读性好的配置格式 |
| 日志 | `loguru` | 结构化审计日志 |
| CLI | `click` 或 `typer` | 命令行界面 |
| 测试 | `pytest` | 单元测试与集成测试 |

### 项目结构

```
watermark/
├── CLAUDE.md                      # 本文件 — 项目规范
├── .env                           # 环境变量（API 密钥，不提交 Git）
├── .gitignore                     # Git 忽略规则
├── requirements.txt               # Python 依赖清单
├── docs/
│   └── research.md                # 盲水印技术研究资料（~250行）
├── tasks/
│   ├── todo.md                    # 开发任务追踪
│   └── lessons.md                 # 纠错经验记录
├── config/
│   ├── settings.yaml              # 全局配置（路径、默认参数）
│   └── watermark_rules.yaml       # 各文件类型的水印策略规则
├── src/
│   ├── __init__.py
│   ├── main.py                    # 主入口 — CLI 命令注册
│   ├── core/                      # 核心逻辑
│   │   ├── __init__.py
│   │   ├── detector.py            # 文件类型检测（magic-bin + filetype + ext）
│   │   ├── router.py              # 水印策略路由分发
│   │   ├── embedder.py            # 水印嵌入统一接口
│   │   ├── extractor.py           # 水印提取统一接口
│   │   └── verifier.py            # 水印完整性校验
│   ├── watermarks/                # 各类型水印实现
│   │   ├── __init__.py
│   │   ├── base.py                # 水印处理器抽象基类
│   │   ├── image_wm.py            # 图像盲水印 (DWT-DCT-SVD)
│   │   ├── pdf_wm.py              # PDF 盲水印（图层+文本）
│   │   ├── office_wm.py           # Office 文档水印
│   │   ├── audio_wm.py            # 音频水印
│   │   ├── video_wm.py            # 视频水印（逐帧）
│   │   └── text_wm.py             # 纯文本水印（零宽字符）
│   ├── ai/                        # AI 集成
│   │   ├── __init__.py
│   │   └── deepseek_client.py     # DeepSeek API 客户端
│   ├── security/                  # 安全模块
│   │   ├── __init__.py
│   │   ├── crypto.py              # 水印内容加密/解密
│   │   ├── key_manager.py         # 密钥生成与管理
│   │   └── audit.py               # 审计日志记录
│   └── utils/                     # 工具函数
│       ├── __init__.py
│       ├── file_utils.py          # 文件操作工具
│       └── validators.py          # 输入校验
└── tests/                         # 测试
    ├── __init__.py
    ├── test_detector.py           # 文件检测测试
    ├── test_image_wm.py           # 图像水印测试
    ├── test_pdf_wm.py             # PDF 水印测试
    ├── test_office_wm.py          # Office 水印测试
    ├── test_crypto.py             # 加密模块测试
    └── test_e2e.py                # 端到端集成测试
```

### 当前阶段
**Phase 0 — 项目初始化**：完成技术调研和项目规划，下一步进入核心模块开发。
详见 `tasks/todo.md`。

---

## 开发者背景

我不是专业开发者，使用 Claude Code 辅助编程。请：
- 代码加中文注释，关键逻辑额外解释
- 遇到复杂问题先给方案让我确认，不要直接大改
- 报错时解释原因 + 修复方案，不要只贴代码
- 优先最简实现，不要过度工程化

---

## 项目专属规范

### 水印系统设计原则

1. **准确性优先**：水印嵌入/提取的正确率 > 99%，宁可降低嵌入强度也不能损坏文件
2. **安全性优先**：水印内容必须加密后再嵌入，密钥与文件分离
3. **文件完整性**：处理后的文件必须可正常打开，功能不受影响
4. **可逆验证**：每次嵌入后必须立即提取验证，确认水印正确
5. **审计可追溯**：每次操作记录完整日志（谁、什么时间、哪个文件、嵌入什么）

### 文件类型检测规则

```
检测流程：
1. python-magic-bin / filetype 读取文件头 (magic bytes) → 得到 MIME 类型
2. 文件扩展名验证 → 得到 ext 类型
3. 两者一致 → 确认类型，路由到对应水印处理器
4. 两者不一致 → 以 magic bytes 为准，记录告警日志
5. 无法识别 → 拒绝处理，记录错误日志
```

### 水印策略路由表

| 文件类型 | MIME 模式 | 水印处理器 | 算法 |
|----------|-----------|------------|------|
| JPG/PNG/BMP/TIFF/WebP | `image/*` | `image_wm.py` | DWT-DCT-SVD |
| PDF | `application/pdf` | `pdf_wm.py` | 图层水印 + 文本水印 |
| DOCX | `application/vnd.openxml*word*` | `office_wm.py` | 图片水印 + 文本水印 |
| XLSX | `application/vnd.openxml*sheet*` | `office_wm.py` | 元数据 + 文本水印 |
| PPTX | `application/vnd.openxml*presentation*` | `office_wm.py` | 图片水印 + 文本水印 |
| MP3/WAV/FLAC | `audio/*` | `audio_wm.py` | DWT-DCT 频域 |
| MP4/AVI/MKV | `video/*` | `video_wm.py` | 逐帧 DWT-DCT-SVD |
| TXT/CSV/JSON/MD | `text/*` | `text_wm.py` | 零宽字符 |

### DeepSeek API 集成规范

```yaml
用途：
  - 分析文件内容敏感度，建议水印嵌入强度
  - 对复杂文档（混合类型）生成最优水印策略
  - 异常检测：识别可能的水印攻击/篡改
  - 生成人类可读的水印报告

接口规范：
  base_url: "https://api.deepseek.com"
  model: "deepseek-chat"  # 或 deepseek-reasoner
  协议: OpenAI 兼容格式
  SDK: openai Python SDK (base_url 替换)

安全要求：
  - API Key 存放在 .env 文件中
  - 不将文件完整内容发送给 API（仅发送元数据/摘要）
  - API 调用失败时 graceful degradation（使用默认策略）
  - 所有 API 调用记录审计日志
```

### 安全架构

```
水印嵌入流程：
1. 生成水印载荷 → {"employee_id": "E001", "timestamp": "...", "file_hash": "..."}
2. JSON 序列化 → 字符串
3. AES-256 加密（密钥从 key_manager 获取）→ 密文
4. 密文编码为比特流
5. 比特流通过纠错编码（BCH）增加冗余
6. 嵌入到文件中

水印提取流程：
1. 从文件中提取比特流
2. BCH 纠错解码
3. AES-256 解密（需要对应密钥）
4. JSON 反序列化 → 水印载荷
5. 校验完整性（hash 比对）
```

---

## 上下文管理规范（核心）

### 1. 文件行数硬限制

| 文件类型 | 最大行数 | 超限动作 |
|----------|----------|----------|
| 单个源代码文件 | **200 行** | 立即拆分为多个文件 |
| 单个模块（目录内所有文件） | **2000 行** | 拆分为子模块 |
| 测试文件 | **300 行** | 按功能拆分测试文件 |
| 配置文件 | **100 行** | 拆分为多个配置文件 |

**每次创建或修改文件后，检查行数。接近限制时主动提醒我。**

### 2. 每个目录必须有 README.md

当一个目录下有 3 个以上文件时，创建 `README.md`，内容：
```markdown
# 目录名

## 用途
一句话说明这个目录做什么。

## 文件清单
- `xxx.py` — 做什么（~行数）
- `yyy.py` — 做什么（~行数）

## 依赖关系
- 本目录依赖：xxx 模块
- 被以下模块依赖：yyy
```

### 3. 定期清理（每 2-3 天新功能开发后执行一次）

当我说 **"清理一下"** 时，执行以下检查：

1. **行数审计**：列出所有超过 150 行的文件，建议拆分方案
2. **死代码检测**：找出没有被 import/调用的函数和文件
3. **TODO 清理**：列出所有 TODO/FIXME/HACK 注释，建议处理方案
4. **一次性脚本**：找出不属于正式功能的临时脚本，建议删除
5. **描述同步**：检查 CLAUDE.md 的项目结构是否与实际目录一致
6. **依赖检查**：requirements.txt 中有无未使用的依赖
7. **水印验证**：对测试文件执行一轮嵌入-提取验证，确认功能正常

---

## Sub-Agent 并行调度规则

### 什么时候并行

**并行派遣**（所有条件满足时）：
- 3+ 个不相关任务
- 不操作同一个文件
- 无输入输出依赖

**顺序派遣**（任一条件触发时）：
- B 需要 A 的输出
- 操作同一文件（合并冲突风险）
- 范围不明确

### Sub-Agent 调用要求

每次派遣 sub-agent 必须指明：
1. 操作哪些文件（写）
2. 读取哪些文件（只读）
3. 完成标准是什么
4. 不许碰哪些文件

### 后台 Agent

研究/分析类任务（不修改文件的）应该后台运行，不阻塞主对话。

---

## 编码规范

### 错误处理
- 所有外部调用（API、文件 IO、数据库）必须 try-except
- 失败时 graceful degradation：显示友好提示 + 使用缓存/默认值，不崩溃
- 日志记录错误详情，但不向用户暴露堆栈信息
- **水印操作失败必须回滚**：不能留下半处理的文件

### 函数设计
- 单个函数不超过 30 行（超过就拆）
- 函数名用动词开头：`embed_watermark()`, `extract_watermark()`, `detect_file_type()`
- 每个函数有 docstring，说明输入输出和可能的异常

### 依赖管理
- 不要自行引入新依赖。需要新库时先问我
- 优先使用标准库，其次是项目已有的依赖
- 每次新增依赖立即更新 requirements.txt

### 配置管理
- 敏感信息（API Key、加密密钥）放 `.env`，通过环境变量读取
- 非敏感配置放 `config/` 目录下的 YAML 文件
- 绝不在代码中硬编码任何密钥或 URL

---

## Git 规范

### Commit 信息格式
```
<类型>: <一句话描述>

类型：feat(新功能) | fix(修复) | refactor(重构) | docs(文档) | chore(杂项) | security(安全)
```

### 每次 commit 前
- 确认没有把 .env、.cache/、__pycache__/ 提交进去
- 确认代码能正常运行（至少不报错）
- 确认水印嵌入/提取的测试通过

---

## 沟通规范

### 当你（AI）不确定时
- **直接说不确定**，不要编造
- 给出 2-3 个可能的方案让我选
- 标明每个方案的优缺点

### 当任务太大时
- 不要一口气全做完
- 先给出拆分计划（5-8 步），让我确认后再逐步执行
- 每完成一步告诉我进度

### 当代码出问题时
- 先说是什么问题（一句话）
- 再说为什么出了这个问题（原因分析）
- 最后给修复方案

### 当我说以下关键词时
| 我说 | 你做 |
|------|------|
| "清理一下" | 执行上面的定期清理流程 |
| "拆一下" | 检查指定文件/模块的行数，给出拆分方案 |
| "健康检查" | 运行完整的项目健康度检查 |
| "现在到哪了" | 总结当前进度，参考 todo.md |
| "省着点" | 减少 token 消耗：回复更简短 |
| "全力跑" | 可以并行、可以大改、不用每步确认 |
| "验证一下" | 对所有已实现的水印类型执行嵌入-提取测试 |

---

## 性能优化规范

### Token 节省策略
1. 修改文件时只输出变更部分，不要重复输出整个文件
2. 长文件只输出相关函数，不要全文输出
3. 使用 `// ... existing code ...` 标记未修改部分

### 上下文保鲜策略
1. 对话超过 20 轮后，主动建议 `/compact` 压缩上下文
2. 切换到完全不同的模块时，建议开新 session
3. 需要大量探索代码库时，使用 sub-agent
4. Debug 时使用 Explore sub-agent 搜索代码

---

## 项目文件模板

### 新模块 Checklist

每次新建一个模块，确保包含：
- [ ] 目录级 README.md
- [ ] 主文件 + 被调用的子文件
- [ ] 每个文件有 docstring + 中文注释
- [ ] 行数全部 < 200
- [ ] 更新 CLAUDE.md 的项目结构
- [ ] 更新 todo.md 的进度

### 新功能 Checklist

每次实现一个新功能，确保：
- [ ] 有错误处理（try-except + 友好提示）
- [ ] 有缓存策略（如果涉及外部 API）
- [ ] 不引入新依赖（或已获批准）
- [ ] 文件行数未超限
- [ ] 能独立测试
- [ ] **水印嵌入后立即提取验证正确性**

### 水印模块 Checklist（本项目专属）

每次新增一种文件类型的水印支持，确保：
- [ ] 实现 `WatermarkBase` 抽象基类的所有方法
- [ ] 在 `watermark_rules.yaml` 中注册路由规则
- [ ] 编写嵌入-提取往返测试
- [ ] 测试至少 3 种常见攻击下的鲁棒性（压缩、缩放、格式转换）
- [ ] 文件处理前后的完整性校验（能正常打开）
- [ ] 更新 docs/research.md 中对应章节的实际验证结果
