"""
水印嵌入服务。

封装核心嵌入逻辑，供 Web 路由通过 run_in_executor 调用。
更新任务进度，确保异常不会逃逸到调用方。
"""

from pathlib import Path

from loguru import logger

from src.core.embedder import embed_watermark
from src.watermarks.base import WatermarkPayload, WatermarkStrength
from src.web.schemas import TaskStatus

# 类型标注用（避免循环导入）
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.web.services.task_manager import TaskManager


def _parse_strength(strength: str) -> WatermarkStrength:
    """将字符串转为 WatermarkStrength 枚举，无效值回退 MEDIUM。"""
    try:
        return WatermarkStrength(strength.lower())
    except ValueError:
        logger.warning(f"无效的水印强度 '{strength}'，使用默认值 medium")
        return WatermarkStrength.MEDIUM


def run_embed(
    task_manager: "TaskManager",
    task_id: str,
    input_path: Path,
    employee_id: str,
    strength: str,
    auto_verify: bool,
    output_dir: Path,
) -> None:
    """
    同步嵌入函数（通过 run_in_executor 在线程池中执行）。

    通过 task_manager 更新进度：
    - 20%: 开始嵌入
    - 80%: 嵌入完成，验证中（如果 auto_verify=True）
    - 100%: 全部完成

    Args:
        task_manager: 任务管理器实例
        task_id: 任务 ID
        input_path: 上传文件路径
        employee_id: 员工 ID
        strength: 水印强度字符串
        auto_verify: 是否自动验证
        output_dir: 输出目录
    """
    try:
        # 阶段1：准备嵌入
        task_manager.update_task(
            task_id, TaskStatus.PROCESSING, 20,
            message="正在嵌入水印...",
            employee_id=employee_id,
        )

        # 构造载荷
        payload = WatermarkPayload(employee_id=employee_id)
        wm_strength = _parse_strength(strength)

        # 阶段2：执行嵌入
        result = embed_watermark(
            input_path=input_path,
            payload=payload,
            output_dir=output_dir,
            strength=wm_strength,
            auto_verify=auto_verify,
        )

        # 阶段3：检查结果
        if not result.success:
            task_manager.update_task(
                task_id, TaskStatus.FAILED, 0,
                message=f"嵌入失败: {result.message}",
            )
            return

        # 嵌入成功
        output_str = str(result.output_path) if result.output_path else ""
        elapsed = f"{result.elapsed_time:.2f}s"
        msg = f"嵌入成功 ({elapsed})"

        # 附加质量指标信息
        if result.quality_metrics:
            psnr = result.quality_metrics.get("psnr")
            if psnr is not None:
                msg += f"，PSNR={psnr:.1f}dB"

        task_manager.update_task(
            task_id, TaskStatus.COMPLETED, 100,
            message=msg,
            output_path=output_str,
        )
        logger.info(f"任务完成: {task_id} -> {output_str}")

    except Exception as e:
        # 捕获所有异常，确保任务状态被更新
        logger.exception(f"嵌入任务异常: {task_id} - {e}")
        task_manager.update_task(
            task_id, TaskStatus.FAILED, 0,
            message=f"嵌入异常: {e}",
        )
