"""Web API 端点测试 — 页面路由、配置/任务/历史 API、嵌入/提取/验证 API。"""

import asyncio
import io
import struct
import zlib
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
import pytest_asyncio
from httpx._transports.asgi import ASGITransport

from src.watermarks.base import EmbedResult, ExtractResult, WatermarkPayload


# ========== 工具函数 ==========

def _make_png_bytes() -> bytes:
    """生成最小合法 PNG（1x1 白色像素）。"""
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    ihdr_crc = zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF
    ihdr = struct.pack(">I", 13) + b"IHDR" + ihdr_data + struct.pack(">I", ihdr_crc)
    compressed = zlib.compress(b"\x00\xFF\xFF\xFF")
    idat_crc = zlib.crc32(b"IDAT" + compressed) & 0xFFFFFFFF
    idat = (struct.pack(">I", len(compressed)) + b"IDAT"
            + compressed + struct.pack(">I", idat_crc))
    iend_crc = zlib.crc32(b"IEND") & 0xFFFFFFFF
    iend = struct.pack(">I", 0) + b"IEND" + struct.pack(">I", iend_crc)
    return b"\x89PNG\r\n\x1a\n" + ihdr + idat + iend


# ========== Fixtures ==========

@pytest_asyncio.fixture
async def client():
    """创建异步测试客户端，手动初始化 TaskManager。"""
    with patch("src.web.services.task_manager.run_cleanup_daemon"):
        from src.web.app import create_app
        from src.web.services.task_manager import TaskManager

        app = create_app()
        app.state.task_manager = TaskManager()
        # raise_app_exceptions=False 避免模板渲染错误导致测试直接崩溃
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
            yield c


# ========== 页面路由测试 ==========

@pytest.mark.asyncio
async def test_redirect_root(client):
    """GET / 应 302 重定向到 /embed。"""
    resp = await client.get("/", follow_redirects=False)
    assert resp.status_code == 302
    assert "/embed" in resp.headers["location"]


@pytest.mark.asyncio
async def test_embed_page(client):
    """GET /embed 路由存在（不返回 404）。"""
    resp = await client.get("/embed")
    assert resp.status_code != 404


@pytest.mark.asyncio
async def test_extract_page(client):
    """GET /extract 路由存在。"""
    resp = await client.get("/extract")
    assert resp.status_code != 404


@pytest.mark.asyncio
async def test_verify_page(client):
    """GET /verify 路由存在。"""
    resp = await client.get("/verify")
    assert resp.status_code != 404


@pytest.mark.asyncio
async def test_history_page(client):
    """GET /history 返回 200 和 HTML。"""
    resp = await client.get("/history")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


# ========== 配置 API 测试 ==========

@pytest.mark.asyncio
async def test_config_endpoint(client):
    """GET /api/config 返回支持的扩展名、大小限制和强度列表。"""
    resp = await client.get("/api/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "supported_extensions" in data
    assert "max_file_size_mb" in data
    assert ".png" in data["supported_extensions"]
    assert data["strengths"] == ["low", "medium", "high"]


# ========== 嵌入 API 错误测试 ==========

@pytest.mark.asyncio
async def test_embed_no_file(client):
    """POST /api/embed 不传文件应返回 400。"""
    resp = await client.post("/api/embed", data={"employee_id": "E001"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_embed_no_employee_id(client):
    """POST /api/embed 传文件但不传 employee_id 应返回 422。"""
    resp = await client.post(
        "/api/embed",
        files={"file": ("test.png", _make_png_bytes(), "image/png")},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_embed_unsupported_format(client):
    """POST /api/embed 传不支持的 .xyz 文件应返回 400。"""
    resp = await client.post(
        "/api/embed",
        files={"file": ("test.xyz", b"fake", "application/octet-stream")},
        data={"employee_id": "E001"},
    )
    assert resp.status_code == 400


# ========== 提取/验证 API 错误测试 ==========

@pytest.mark.asyncio
async def test_extract_no_file(client):
    """POST /api/extract 不传文件应返回 400。"""
    resp = await client.post("/api/extract", data={"strength": "medium"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_verify_no_file(client):
    """POST /api/verify 不传文件应返回 400。"""
    resp = await client.post("/api/verify", data={"expected_id": ""})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_verify_batch_no_files(client):
    """POST /api/verify/batch 不传文件应返回 400。"""
    resp = await client.post("/api/verify/batch", data={"expected_id": ""})
    assert resp.status_code == 400


# ========== 任务 API 测试 ==========

@pytest.mark.asyncio
async def test_task_not_found(client):
    """GET /api/tasks/nonexistent 应返回 404。"""
    resp = await client.get("/api/tasks/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_history_empty(client):
    """GET /api/tasks/history 初始应返回空列表。"""
    resp = await client.get("/api/tasks/history")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_download_not_found(client):
    """GET /api/embed/nonexistent/download 应返回 404。"""
    resp = await client.get("/api/embed/nonexistent/download")
    assert resp.status_code == 404


# ========== Mock 核心函数的集成测试 ==========

@pytest.mark.asyncio
async def test_embed_with_mock(client, tmp_path):
    """POST /api/embed 传有效 PNG（mock 核心嵌入），验证任务创建。"""
    out_file = tmp_path / "wm_test.png"
    out_file.write_bytes(_make_png_bytes())
    mock_result = EmbedResult(
        success=True, output_path=out_file,
        message="嵌入成功", elapsed_time=0.5,
    )
    with patch("src.web.services.embed_service.embed_watermark", return_value=mock_result):
        resp = await client.post(
            "/api/embed",
            files={"file": ("test.png", _make_png_bytes(), "image/png")},
            data={"employee_id": "E001", "strength": "medium"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "task_id" in data
    assert len(data["task_id"]) == 12  # uuid4 前 12 位
    assert data["message"] != ""


@pytest.mark.asyncio
async def test_extract_with_mock(client):
    """POST /api/extract 传 PNG（mock 核心提取），验证返回结果。"""
    mock_payload = WatermarkPayload(
        employee_id="E001", timestamp="2026-04-05T00:00:00Z",
    )
    mock_result = ExtractResult(
        success=True, payload=mock_payload,
        confidence=0.95, message="提取成功",
    )
    with patch("src.web.services.extract_service.extract_watermark", return_value=mock_result):
        resp = await client.post(
            "/api/extract",
            files={"file": ("test.png", _make_png_bytes(), "image/png")},
            data={"strength": "medium"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["employee_id"] == "E001"
    assert data["confidence"] == pytest.approx(0.95)


@pytest.mark.asyncio
async def test_verify_with_mock(client):
    """POST /api/verify 传 PNG（mock 核心验证），验证返回结果。"""
    from src.core.verifier import VerifyResult

    mock_vr = VerifyResult(
        success=True, file_path=Path("dummy.png"),
        employee_id="E001", matched=True, message="验证通过",
    )
    with patch("src.web.services.extract_service.verify_file", return_value=mock_vr):
        resp = await client.post(
            "/api/verify",
            files={"file": ("test.png", _make_png_bytes(), "image/png")},
            data={"expected_id": "E001", "strength": "medium"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["matched"] is True
    assert data["employee_id"] == "E001"
