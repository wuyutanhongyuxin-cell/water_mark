"""
任务管理器测试。

测试 TaskManager 的核心功能，包括：
- 任务创建/查询/更新
- 历史记录分页和过滤
- SSE 事件订阅
- 清理功能
"""

import asyncio
from unittest.mock import patch

import pytest

from src.web.schemas import TaskStatus


# ========== Fixtures ==========

@pytest.fixture
def tm():
    """创建 TaskManager 实例，patch 守护线程避免副作用。"""
    with patch("src.web.services.task_manager.run_cleanup_daemon"):
        from src.web.services.task_manager import TaskManager
        return TaskManager()


# ========== 任务创建与查询 ==========

def test_create_task(tm):
    """create_task 应返回 12 位十六进制 ID。"""
    task_id = tm.create_task("test.png", "embed")
    assert len(task_id) == 12
    # 确认是合法的十六进制字符串
    int(task_id, 16)


def test_get_task(tm):
    """get_task 返回 TaskResponse，字段正确。"""
    task_id = tm.create_task("doc.pdf", "extract")
    resp = tm.get_task(task_id)

    assert resp is not None
    assert resp.task_id == task_id
    assert resp.filename == "doc.pdf"
    assert resp.status == TaskStatus.PENDING
    assert resp.progress == 0
    assert resp.created_at != ""


def test_get_nonexistent_task(tm):
    """查询不存在的任务应返回 None。"""
    result = tm.get_task("does_not_exist")
    assert result is None


# ========== 任务更新 ==========

def test_update_task_progress(tm):
    """更新任务后，状态和进度应改变。"""
    task_id = tm.create_task("img.png", "embed")
    tm.update_task(task_id, TaskStatus.PROCESSING, 50, "处理中...")

    resp = tm.get_task(task_id)
    assert resp.status == TaskStatus.PROCESSING
    assert resp.progress == 50
    assert resp.message == "处理中..."


def test_update_task_completed(tm):
    """任务完成后应被添加到历史记录。"""
    task_id = tm.create_task("img.png", "embed")
    tm.update_task(task_id, TaskStatus.COMPLETED, 100, "嵌入成功")

    # 确认状态已更新
    resp = tm.get_task(task_id)
    assert resp.status == TaskStatus.COMPLETED
    assert resp.progress == 100

    # 确认已写入历史
    items, total = tm.get_history(1, 10)
    assert total == 1
    assert items[0].task_id == task_id
    assert items[0].status == "completed"


def test_update_task_failed(tm):
    """任务失败后也应被添加到历史记录。"""
    task_id = tm.create_task("bad.docx", "embed")
    tm.update_task(task_id, TaskStatus.FAILED, 0, "格式错误")

    items, total = tm.get_history(1, 10)
    assert total == 1
    assert items[0].status == "failed"
    assert items[0].message == "格式错误"


# ========== 历史记录 ==========

def test_history_empty(tm):
    """初始状态历史记录为空。"""
    items, total = tm.get_history(1, 10)
    assert total == 0
    assert items == []


def test_history_pagination(tm):
    """创建 5 个已完成任务，验证分页正确。"""
    for i in range(5):
        tid = tm.create_task(f"file_{i}.png", "embed")
        tm.update_task(tid, TaskStatus.COMPLETED, 100, f"ok_{i}")

    # 第 1 页（每页 3 条，最新在前）
    page1, total = tm.get_history(1, 3)
    assert total == 5
    assert len(page1) == 3
    # 最新记录排在前面
    assert page1[0].message == "ok_4"

    # 第 2 页
    page2, total2 = tm.get_history(2, 3)
    assert total2 == 5
    assert len(page2) == 2


def test_history_filter(tm):
    """按操作类型过滤历史记录。"""
    # 创建不同类型的任务并完成
    tid1 = tm.create_task("a.png", "embed")
    tm.update_task(tid1, TaskStatus.COMPLETED, 100, "ok")

    tid2 = tm.create_task("b.png", "extract")
    tm.update_task(tid2, TaskStatus.COMPLETED, 100, "ok")

    tid3 = tm.create_task("c.png", "embed")
    tm.update_task(tid3, TaskStatus.COMPLETED, 100, "ok")

    # 过滤 embed 类型
    embed_items, embed_total = tm.get_history(1, 10, operation="embed")
    assert embed_total == 2

    # 过滤 extract 类型
    ext_items, ext_total = tm.get_history(1, 10, operation="extract")
    assert ext_total == 1
    assert ext_items[0].operation == "extract"


# ========== 输出路径 ==========

def test_get_output_path(tm):
    """设置 output_path 后可通过 get_output_path 获取。"""
    task_id = tm.create_task("test.png", "embed")
    # output_path 通过 extra 参数传入 update_task
    tm.update_task(
        task_id, TaskStatus.COMPLETED, 100, "ok",
        output_path="/tmp/wm_test.png",
    )

    path = tm.get_output_path(task_id)
    assert path == "/tmp/wm_test.png"


def test_get_output_path_nonexistent(tm):
    """查询不存在的任务返回 None。"""
    assert tm.get_output_path("no_such_task") is None


# ========== SSE 事件订阅 ==========

@pytest.mark.asyncio
async def test_sse_subscribe(tm):
    """订阅任务事件流，更新任务后应收到事件。"""
    task_id = tm.create_task("test.png", "embed")

    events = []

    async def collect_events():
        """收集第一个事件后停止。"""
        async for event in tm.subscribe(task_id):
            events.append(event)
            break  # 拿到第一个事件即停

    # 启动订阅协程
    task = asyncio.create_task(collect_events())
    # 短暂等待，确保订阅者已注册
    await asyncio.sleep(0.1)

    # 触发事件：将任务标记为完成
    tm.update_task(task_id, TaskStatus.COMPLETED, 100, "done")

    # 等待收集完成（加超时避免永久阻塞）
    await asyncio.wait_for(task, timeout=5.0)

    # 至少收到 1 个事件
    assert len(events) >= 1
    # 事件应包含 "data:" 前缀格式的 SSE 数据
    assert "completed" in events[0]


# ========== 清理 ==========

def test_cleanup(tm):
    """cleanup_old_files 应委托给 cleanup 模块。"""
    with patch("src.web.services.task_manager.cleanup_old_files") as mock_cleanup:
        mock_cleanup.return_value = 3
        tm.cleanup_old_files(max_age_minutes=10)
        mock_cleanup.assert_called_once_with(10)
