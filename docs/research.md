# 盲水印 / 暗水印 技术研究资料

> 整理时间：2026-04-03 | 用途：项目开发参考 | 来源：联网搜索 + 学术文献

---

## 一、基本概念

### 1.1 盲水印 vs 非盲水印

| 特性 | 盲水印 (Blind) | 非盲水印 (Non-blind) | 半盲水印 (Semi-blind) |
|------|---------------|---------------------|---------------------|
| 提取时需原图 | **否** | 是 | 否（需辅助信息） |
| 实用性 | 高 | 低 | 中 |
| 鲁棒性设计难度 | 高 | 低（有原图参照） | 中 |
| 典型场景 | 版权保护、泄露追踪 | 篡改检测 | 认证 |

### 1.2 空域 vs 频域

| 方法 | 原理 | 优点 | 缺点 |
|------|------|------|------|
| **空域 (LSB)** | 直接修改像素最低有效位 | 简单、容量大 | 鲁棒性差 |
| **频域** | 在频率空间嵌入水印 | 隐匿性强、抗攻击强 | 计算复杂度高 |

---

## 二、核心频域算法

### 2.1 DCT（离散余弦变换）

- **原理**：8×8 分块 → DCT 变换 → 中频系数嵌入水印
- **优势**：JPEG 压缩本身基于 DCT，天然抗 JPEG
- **嵌入策略**：量化索引调制 (QIM)、扩频 (Spread Spectrum)
- **经典**：Cox 等人 (1997) 扩频水印

### 2.2 DWT（离散小波变换）

- **原理**：多级小波分解 → LL/LH/HL/HH 子带 → 在中低频子带嵌入
- **优势**：多分辨率分析、与 HVS 适配、兼容 JPEG2000
- **常用小波基**：Haar、Daubechies (db1-db8)
- **通常组合使用**：DWT+DCT 或 DWT+SVD

### 2.3 DFT（离散傅里叶变换）

- **原理**：傅里叶频域中频环形区域嵌入
- **核心优势**：**抗几何攻击能力最强**
  - 平移不变性（幅度谱不变）
  - 旋转等变性（可通过对数极坐标变换处理）
- **缺点**：容量有限、计算量大

### 2.4 SVD（奇异值分解）

- **原理**：A = USV^T，修改奇异值嵌入水印
- **特性**：奇异值代表图像内蕴特性，**稳定性极好**
- **注意**：存在"虚警问题"（false positive），需特殊设计规避
- **常与 DWT/DCT 组合**

### 2.5 组合方案对比

| 方法 | 抗压缩 | 抗几何 | 不可见性 | 容量 | 计算量 |
|------|--------|--------|----------|------|--------|
| LSB | 差 | 差 | 中 | 高 | 低 |
| DCT | 好 | 中 | 好 | 中 | 中 |
| DWT | 好 | 中 | 很好 | 中 | 中 |
| DFT | 中 | **很好** | 好 | 低 | 高 |
| DWT+DCT | 很好 | 中 | 很好 | 中 | 高 |
| DWT+SVD | 很好 | 好 | 很好 | 中 | 高 |
| DWT+DCT+SVD | **最强** | 好 | 很好 | 中 | 最高 |

---

## 三、深度学习水印方法

| 方法 | 来源 | 核心思路 | 特点 |
|------|------|----------|------|
| **HiDDeN** | Zhu 2018 | 编码器+噪声层+解码器端到端训练 | 开创性工作 |
| **StegaStamp** | Tancik, CVPR 2020 | STN处理透视变换 | **抗打印-拍照**攻击 |
| **RivaGAN** | Zhang 2019 | 注意力机制+对抗网络 | 自动找最优嵌入区域 |
| **Stable Signature** | Meta, ICCV 2023 | 微调扩散模型解码器 | 生成即带水印 |
| **Tree-Ring** | Wen, NeurIPS 2023 | 初始噪声傅里叶空间嵌入 | 抗裁剪/旋转/缩放 |
| **PRC-Watermark** | Zhao, ICLR 2025 | 不可检测的生成式水印 | 最新方案 |

---

## 四、各文件类型最优水印策略

### 4.1 图像文件 (JPG/PNG/BMP/TIFF/WebP)

| 策略 | 推荐算法 | 说明 |
|------|----------|------|
| **首选** | DWT-DCT-SVD | 鲁棒性最强的传统方案 |
| 高性能需求 | DWT-DCT | 速度与鲁棒性平衡（~300ms/1080P） |
| 深度学习 | RivaGAN / StegaStamp | 需 GPU，效果最好 |

**推荐库**：
- `blind-watermark` (pip) — DWT-DCT-SVD，最流行
- `invisible-watermark` (pip) — dwtDct/dwtDctSvd/rivaGan

### 4.2 PDF 文件

| 策略 | 说明 |
|------|------|
| **图层水印** | 渲染 PDF 页面为图像 → 嵌入盲水印 → 重建 PDF |
| **元数据水印** | 在 PDF 元数据/隐藏注释中嵌入信息 |
| **文本水印** | 对 PDF 中的文本内容使用零宽字符水印 |
| **组合策略** | 图层水印 + 文本水印同时嵌入（推荐） |

**推荐库**：`PyMuPDF (fitz)`, `pdf2image`, `Pillow`, `blind-watermark`

### 4.3 Office 文档 (DOCX/XLSX/PPTX)

| 策略 | 说明 |
|------|------|
| **图像水印** | 提取嵌入图片 → 加盲水印 → 回写 |
| **文本水印** | 零宽字符/Unicode 同形字嵌入文本内容 |
| **格式水印** | 微调字间距/行间距编码信息 |
| **元数据水印** | 在文档属性/自定义字段中嵌入 |

**推荐库**：`python-docx`, `openpyxl`, `python-pptx`, `text_blind_watermark`

### 4.4 音频文件 (MP3/WAV/FLAC)

| 策略 | 说明 |
|------|------|
| **频域嵌入** | FFT/MDCT 系数 + 心理声学掩蔽模型 |
| **DWT-DCT** | 小波变换后在系数中嵌入 |
| **扩频** | CDMA 类扩频嵌入 |

**推荐库/工具**：`audiowmark`, `AudioSeal` (Meta)

### 4.5 视频文件 (MP4/AVI/MKV)

| 策略 | 说明 |
|------|------|
| **逐帧图像水印** | 关键帧提取 → 图像盲水印 → 重新编码 |
| **3D 变换域** | 3D-DWT/DCT 时空联合嵌入 |
| **压缩域** | 直接修改 H.264/H.265 的 DCT 系数 |

**推荐库**：`VideoSeal` (Meta), `blind-video-watermark`, `FFmpeg` + 图像水印

### 4.6 纯文本文件 (TXT/CSV/JSON/代码)

| 策略 | 说明 |
|------|------|
| **零宽字符** | 插入 ZWSP/ZWJ/ZWNJ 等不可见字符 |
| **Unicode 同形字** | 视觉相同但编码不同的字符替换 |
| **空白编码** | 行尾空格/Tab 编码比特 |

**推荐库**：`text_blind_watermark`

---

## 五、鲁棒性与攻击

### 5.1 常见攻击类型

- **信号处理**：JPEG 压缩、高斯噪声、滤波、直方图均衡化
- **几何攻击**：旋转、缩放、裁剪、平移、仿射变换
- **去除攻击**：多副本平均、去噪算法、AI 去水印
- **协议攻击**：逆向攻击、复制攻击

### 5.2 抗攻击策略

- 冗余嵌入 + 多数表决
- 纠错编码（BCH/Turbo/LDPC）
- 同步模板检测几何变换
- SIFT/Harris 特征点几何同步
- 自适应嵌入（根据局部纹理/边缘调节强度）

### 5.3 质量评估指标

| 指标 | 说明 | 合格标准 |
|------|------|----------|
| **PSNR** | 峰值信噪比 | > 38-42 dB |
| **SSIM** | 结构相似性 | > 0.95 |
| **NC** | 归一化相关系数 | > 0.9 |
| **BER** | 误码率 | < 0.1 |

---

## 六、LLM 文本水印（大模型水印）

### 6.1 核心方法

| 方法 | 原理 | 优缺点 |
|------|------|--------|
| **绿名单/红名单** | 根据前 token 哈希分词表，偏向绿色 token | 有效但略影响质量 |
| **无失真水印** | 逆变换采样保持分布不变 | 无质量损失但检测力弱 |
| **语义水印 (SemStamp)** | 句子级语义空间嵌入 | 抗改写但复杂 |
| **多比特水印** | 嵌入用户 ID/时间戳等多比特信息 | 可溯源 |

### 6.2 关键工具

- **MarkLLM** (清华, EMNLP 2024) — 最完善的 LLM 水印工具箱
- **lm-watermarking** (Kirchenbauer) — 经典绿名单实现
- **Google SynthID** — Gemini 使用的商业方案

---

## 七、重要 GitHub 仓库索引

### 图像盲水印
- [guofei9987/blind_watermark](https://github.com/guofei9987/blind_watermark) — **最流行** DWT-DCT-SVD Python 库
- [ShieldMnt/invisible-watermark](https://github.com/ShieldMnt/invisible-watermark) — Stable Diffusion 默认库
- [Stability-AI/invisible-watermark-gpu](https://github.com/Stability-AI/invisible-watermark-gpu) — GPU 加速版
- [chishaxie/BlindWaterMark](https://github.com/chishaxie/BlindWaterMark) — DFT 频域经典实现
- [fire-keeper/BlindWatermark](https://github.com/fire-keeper/BlindWatermark) — 知识产权保护
- [lishuaijuly/Watermark](https://github.com/lishuaijuly/watermark) — LSB + DWT+SVD 学习对比

### 深度学习水印
- [tancik/StegaStamp](https://github.com/tancik/StegaStamp) — CVPR 2020 抗打印拍照
- [DAI-Lab/RivaGAN](https://github.com/DAI-Lab/RivaGAN) — 注意力+对抗网络
- [dnn-security/Watermark-Robustness-Toolbox](https://github.com/dnn-security/Watermark-Robustness-Toolbox) — IEEE S&P'22 评估工具

### AIGC / 扩散模型水印
- [YuxinWenRick/tree-ring-watermark](https://github.com/YuxinWenRick/tree-ring-watermark) — NeurIPS 2023
- [facebookresearch/stable_signature](https://github.com/facebookresearch/stable_signature) — Meta 扩散模型签名
- [XuandongZhao/PRC-Watermark](https://github.com/XuandongZhao/PRC-Watermark) — ICLR 2025
- [XuandongZhao/WatermarkAttacker](https://github.com/XuandongZhao/WatermarkAttacker) — NeurIPS 2024 去水印攻击

### Meta Seal 全模态套件 (MIT)
- [facebookresearch/meta-seal](https://github.com/facebookresearch/meta-seal) — 统一框架
- [facebookresearch/audioseal](https://github.com/facebookresearch/audioseal) — 音频 SOTA
- [facebookresearch/videoseal](https://github.com/facebookresearch/videoseal) — 视频水印
- [facebookresearch/textseal](https://github.com/facebookresearch/textseal) — LLM 文本水印

### 文本水印
- [guofei9987/text_blind_watermark](https://github.com/guofei9987/text_blind_watermark) — 零宽字符文本水印
- [XuandongZhao/Unigram-Watermark](https://github.com/XuandongZhao/Unigram-Watermark) — ICLR 2024

### LLM 大模型水印
- [THU-BPM/MarkLLM](https://github.com/THU-BPM/MarkLLM) — EMNLP 2024 清华工具箱
- [jwkirchenbauer/lm-watermarking](https://github.com/jwkirchenbauer/lm-watermarking) — 经典实现
- [THU-BPM/unforgeable_watermark](https://github.com/THU-BPM/unforgeable_watermark) — ICLR 2024

### 音频/视频水印
- [swesterfeld/audiowmark](https://github.com/swesterfeld/audiowmark) — patchwork 音频盲水印
- [eluv-io/blind-video-watermark](https://github.com/eluv-io/blind-video-watermark) — DT-CWT 视频水印

### Awesome Lists
- [and-mill/Awesome-GenAI-Watermarking](https://github.com/and-mill/Awesome-GenAI-Watermarking) — 生成式 AI 水印精选
- [Kaicheng-Yang0828/Invisible-Watermarking-paper-list](https://github.com/Kaicheng-Yang0828/Invisible-Watermarking-paper-list) — 论文列表

---

## 八、企业文档水印系统设计要点

### 8.1 动态水印 vs 静态水印

| 类型 | 说明 | 适用场景 |
|------|------|----------|
| **动态水印** | 实时生成，含用户名/IP/时间戳 | 泄露追踪 |
| **静态水印** | 固定内容如公司名称 | 版权标识 |

### 8.2 架构关键点

1. **文件类型自动检测**：magic bytes + 扩展名双重验证
2. **策略路由**：根据文件类型自动选择最优水印算法
3. **密钥管理**：AES 加密水印内容，密钥分离存储
4. **审计日志**：记录每次水印操作的完整链路
5. **DeepSeek API 集成**：智能分析文件内容、生成水印策略建议

### 8.3 安全考量

- 水印内容加密后再嵌入
- 密钥不随文件传输
- 支持水印完整性校验
- 审计日志不可篡改
- API 密钥通过环境变量管理
