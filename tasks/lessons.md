# WatermarkForge — 纠错经验记录

> 每次被用户纠正或发现问题时，记录在此。

---

## 2026-04-03: Phase 1 三方代码审查发现

### 1. 回滚可删除原文件 (Critical)
- **问题**: embedder 的 `_rollback()` 会删除 output_path，但未检查 output == input
- **修复**: 在嵌入前检查 `output_path.resolve() == input_path.resolve()`
- **教训**: 涉及文件删除的操作必须做路径安全检查

### 2. 验证异常 fail-open (Critical)
- **问题**: verify() 抛异常时被标记为 non-fatal，返回 success=True
- **修复**: 改为 fail-closed，异常触发回滚
- **教训**: 安全相关的验证必须 fail-closed，不能 graceful degradation

### 3. OOXML 被识别为 ZIP (Major)
- **问题**: .docx/.xlsx/.pptx 的 magic bytes 是 ZIP，python-magic 返回 application/zip
- **修复**: 对 ZIP + Office 扩展名做特判
- **教训**: Office 文件需要特殊处理，不能简单依赖 magic bytes

### 4. 动态导入安全 (Major)
- **问题**: importlib.import_module() 从 YAML 读取路径，无验证
- **修复**: 正则白名单 `^[a-zA-Z_]\w*\.[A-Za-z_]\w*$` + 强制 `src.watermarks.` 前缀
- **教训**: 从配置文件读取的路径用于动态导入时，必须做白名单校验

### 5. 配置声明但不生效 (Major)
- **问题**: settings.yaml 的 overwrite、max_file_size 等配置未被代码使用
- **修复**: 在 embedder 中实际读取和执行配置
- **教训**: 不要写"看起来可控实际不生效"的死配置

### 6. Python 类型注解兼容性
- **问题**: `WatermarkPayload | None` 语法在 Python 3.9 报 TypeError
- **修复**: 使用 `Optional[WatermarkPayload]`
- **教训**: 除非确认 Python 3.10+，否则用 `Optional` 或 `from __future__ import annotations`

### 7. blind-watermark wm_size 问题
- **问题**: 提取时必须提供 wm_size，但字符串模式的 wm_size 不可预测
- **修复**: 使用固定 64 字节 = 512 bits 的 bit 编码方案
- **教训**: 设计水印系统时，提取参数必须是已知的或可推断的

---

## 2026-04-04: Phase 3 安全模块开发发现

### 8. python-magic 不支持 Windows 中文路径 (Major)
- **问题**: `magic.from_file()` 和 `filetype.guess(path)` 无法处理含中文的文件路径
- **修复**: 先 `path.read_bytes()[:8192]` 读取文件头，用 `magic.from_buffer()` 和 `filetype.guess(bytes)` 检测
- **教训**: Windows 上涉及文件路径的 C 扩展库（python-magic）普遍不支持非 ASCII 路径，优先用 buffer 方式

### 9. cv2.imread/imwrite 不支持 Windows 中文路径 (Major)
- **问题**: `cv2.imread()` 和 `cv2.imwrite()` 无法读写中文路径文件，blind-watermark 内部也用这些函数
- **修复**: 用 `cv2.imdecode(np.frombuffer(...))` 和 `cv2.imencode()` 替代；blind-watermark 用 `bwm.bwm_core.read_img_arr(img)` 和 `bwm.extract(embed_img=img)` 替代 filename 参数
- **教训**: 任何 C++ 后端的图像库在 Windows 上都可能有中文路径问题，统一用 bytes 接口

### 10. rstrip(b"\x00") 会误删密文末尾零字节 (Critical)
- **问题**: AES-GCM 密文可能以 0x00 结尾，rstrip 会破坏密文导致解密失败
- **修复**: v2 格式用 `encrypted_len` 字段精确记录密文长度，提取时按长度截取
- **教训**: 加密数据是随机 bytes，不能用任何 strip/rstrip 处理

### 11. 256x256 图像不够嵌入 1024 bits (Minor)
- **问题**: blind-watermark 对 256x256 图像的 block_num 恰好等于 1024，而嵌入要求 wm_size < block_num
- **修复**: 文档标注最小图像尺寸为 257x257+（实际大多数图片远大于此）
- **教训**: block_num 计算公式 = (H//4 // 4) * (W//4 // 4)，临界值需严格小于

---

## 2026-04-04: Phase 3 代码审查（三方审查）修复

### 12. 提取时 attacker-controlled key_id 可自动生成密钥文件 (Critical)
- **问题**: `_decode_v2()` 从水印数据读取 `key_id`（0-255），`get_key()` 会对不存在的 key_id 自动生成密钥文件，恶意图片可创建 256 个密钥文件
- **修复**: `get_key()` 加 `auto_generate` 参数，提取时传 `auto_generate=False`，密钥不存在时返回 None
- **教训**: 从不可信数据（水印提取结果）读取的参数传入文件系统操作时，必须禁止自动创建行为

### 13. 审计日志初始化非线程安全 (Major)
- **问题**: `audit.py` 的 `_ensure_init()` 用全局 `_initialized` 无锁保护，`max_workers:4` 多线程下可导致重复 `logger.add()` 产生重复审计条目
- **修复**: 加 `threading.Lock` + double-check locking
- **教训**: 任何全局懒初始化都必须考虑线程安全，尤其是涉及 I/O 资源（日志 sink）时

### 14. embedder 多个失败路径缺少审计日志 (Major)
- **问题**: pre-check、output-path-check、routing、validation 四个失败路径无 `log_embed()` 调用，审计日志不完整
- **修复**: 在所有失败退出路径前添加 `log_embed()` 调用
- **教训**: 审计日志要覆盖所有退出路径（成功+失败），"只记成功不记失败"等于没有审计

### 15. _imwrite_safe 返回值未检查导致静默数据丢失 (Major)
- **问题**: `cv2.imencode` 或 `write_bytes` 失败时 `embed()` 仍返回 `success=True`
- **修复**: 检查 `_imwrite_safe` 返回值，失败时返回 `EmbedResult(success=False)`
- **教训**: 文件写入操作的返回值/异常必须检查，否则可能"嵌入成功但文件没写出去"

### 16. crypto.py 异常捕获过宽暴露加密细节 (Minor)
- **问题**: `except Exception as e` 捕获所有异常并将 `{e}` 写入日志，可能泄露加密实现细节；也会掩盖编程错误
- **修复**: 改为捕获 `cryptography.exceptions.InvalidTag`，日志用固定消息 "authentication tag mismatch"
- **教训**: 加密相关异常处理要精确捕获 + 固定消息，不暴露内部状态

### 17. Employee ID 明文出现在非审计日志 (Minor)
- **问题**: `image_wm.py` 的 `logger.info()` 输出完整 employee_id，非审计日志可能被更多人访问
- **修复**: 脱敏处理，如 `REVIEW001` → `RE***1`
- **教训**: PII（个人可识别信息）在非审计日志中应脱敏

---

## 2026-04-04: Phase 4 PDF/Office/Text 水印开发发现

### 18. PDF 纯白页面频域纹理不足导致 DWT-DCT-SVD 嵌入失败 (Critical)
- **问题**: PDF 页面以大面积白色为主，DWT-DCT-SVD 算法需要足够的频域纹理才能稳定嵌入/提取。纯白页面嵌入后立即提取都返回 None
- **修复**: 嵌入前对第一页添加微弱高斯噪声（sigma=3，PSNR≈40dB），使用固定种子确保可重复
- **教训**: DWT-DCT-SVD 盲水印依赖图像纹理复杂度，低纹理图像（文档页面、纯色图）需要预处理

### 19. cv2.imencode 内部已处理 BGR→RGB 转换 (Major)
- **问题**: `cv2.imencode(".png", img)` 内部自动将 BGR 转为 RGB 写入 PNG。如果先手动 `cvtColor(BGR→RGB)` 再传给 imencode，通道会被二次交换导致颜色错误
- **修复**: 直接将 BGR 数组传给 imencode，不做预转换
- **教训**: 理解 OpenCV 的 BGR 约定——imencode/imwrite 内部处理转换，不要手动重复

### 20. OOXML 检测：python-magic 可能返回 octet-stream 而非 zip (Major)
- **问题**: 某些 DOCX/PPTX 文件被 python-magic-bin 检测为 `application/octet-stream` 而非 `application/zip`，导致 OOXML 特判不触发，路由失败
- **修复**: 在 detector.py 的 OOXML 特判中增加 `application/octet-stream` 匹配
- **教训**: python-magic-bin 对同类文件的检测结果不一致，OOXML 特判需要覆盖更多 fallback MIME 类型
