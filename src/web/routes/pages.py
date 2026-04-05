"""
HTML 页面路由。

提供前端页面渲染，使用 Jinja2 模板引擎。
每个页面对应一个 GET 端点。
"""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["pages"])

# 模板目录：项目根目录 / templates
_project_root = Path(__file__).resolve().parent.parent.parent.parent
_templates_dir = _project_root / "templates"
templates = Jinja2Templates(directory=str(_templates_dir))


@router.get("/")
async def index():
    """根路径重定向到嵌入页面。"""
    return RedirectResponse(url="/embed", status_code=302)


@router.get("/embed")
async def embed_page(request: Request):
    """水印嵌入页面。"""
    return templates.TemplateResponse("embed.html", {"request": request})


@router.get("/extract")
async def extract_page(request: Request):
    """水印提取页面。"""
    return templates.TemplateResponse("extract.html", {"request": request})


@router.get("/verify")
async def verify_page(request: Request):
    """水印验证页面。"""
    return templates.TemplateResponse("verify.html", {"request": request})


@router.get("/history")
async def history_page(request: Request):
    """操作历史页面。"""
    return templates.TemplateResponse("history.html", {"request": request})
