"""
FastAPI 应用工厂。

创建和配置 Web 应用实例，包括：
- 生命周期管理（启动/关闭）
- 静态文件与模板挂载
- 路由注册
- 任务管理器初始化
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from loguru import logger

from src.web.dependencies import get_output_dir, get_upload_dir
from src.web.routes import api_router, page_router
from src.web.services.task_manager import TaskManager

# 项目根目录
_project_root = Path(__file__).resolve().parent.parent.parent
_static_dir = _project_root / "static"
_templates_dir = _project_root / "templates"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时初始化资源，关闭时清理。"""
    # === 启动阶段 ===
    logger.info("WatermarkForge Web UI 启动中...")

    # 确保必要目录存在
    get_upload_dir()
    get_output_dir()
    _static_dir.mkdir(parents=True, exist_ok=True)
    _templates_dir.mkdir(parents=True, exist_ok=True)

    # 初始化任务管理器（单例，挂载到 app.state）
    app.state.task_manager = TaskManager()
    logger.info("任务管理器已初始化")

    logger.info("WatermarkForge Web UI 启动完成")
    yield

    # === 关闭阶段 ===
    logger.info("WatermarkForge Web UI 关闭中...")
    # 清理过期临时文件
    try:
        app.state.task_manager.cleanup_old_files(max_age_minutes=0)
    except Exception as e:
        logger.warning(f"关闭时清理文件失败: {e}")
    logger.info("WatermarkForge Web UI 已关闭")


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例。"""
    app = FastAPI(
        title="WatermarkForge",
        description="企业文档盲水印自动化系统 Web UI",
        version="0.1.0",
        lifespan=lifespan,
    )

    # 挂载静态文件（CSS/JS/图片等）
    if _static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

    # 注册 API 路由（/api/*）
    app.include_router(api_router)

    # 注册页面路由（HTML 页面）
    app.include_router(page_router)

    return app


# 模块级应用实例（供 uvicorn 直接引用）
app = create_app()
