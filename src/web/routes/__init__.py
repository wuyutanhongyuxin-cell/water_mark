"""
Web 路由注册中心。

将所有子路由统一注册到 api_router，
由 app.py 的 create_app() 一次性挂载。
"""

from fastapi import APIRouter

from src.web.routes.pages import router as pages_router
from src.web.routes.api_embed import router as embed_router
from src.web.routes.api_extract import router as extract_router
from src.web.routes.api_verify import router as verify_router
from src.web.routes.api_tasks import router as tasks_router

# API 路由（所有 /api/* 接口）
api_router = APIRouter()
api_router.include_router(embed_router)
api_router.include_router(extract_router)
api_router.include_router(verify_router)
api_router.include_router(tasks_router)

# 页面路由（HTML 页面）
page_router = pages_router

__all__ = ["api_router", "page_router"]
