"""
Pydantic v2 数据模型定义。

定义 Web API 的请求/响应数据结构，包括：
- 嵌入请求与响应
- 提取响应
- 验证响应（单文件/批量）
- 任务状态与历史记录
- 系统配置
"""

from enum import Enum

from pydantic import BaseModel, Field


# ========== 嵌入相关 ==========

class EmbedRequest(BaseModel):
    """水印嵌入请求参数。"""
    employee_id: str = Field(..., min_length=1, description="员工唯一标识")
    strength: str = Field(default="medium", description="水印强度: low/medium/high")
    auto_verify: bool = Field(default=True, description="嵌入后是否自动验证")


class EmbedResponse(BaseModel):
    """水印嵌入响应（立即返回任务 ID）。"""
    task_id: str = Field(..., description="异步任务 ID")
    message: str = Field(default="", description="提示信息")


# ========== 提取相关 ==========

class ExtractResponse(BaseModel):
    """水印提取响应。"""
    success: bool = Field(..., description="是否成功提取")
    employee_id: str = Field(default="", description="提取到的员工 ID")
    timestamp: str = Field(default="", description="水印嵌入时间")
    confidence: float = Field(default=0.0, description="提取置信度 0.0~1.0")
    message: str = Field(default="", description="结果描述")


# ========== 验证相关 ==========

class VerifyResponse(BaseModel):
    """单文件验证响应。"""
    success: bool = Field(..., description="是否成功提取到水印")
    employee_id: str = Field(default="", description="提取到的员工 ID")
    matched: bool = Field(default=False, description="是否与预期 ID 匹配")
    message: str = Field(default="", description="结果描述")


class VerifyBatchItem(BaseModel):
    """批量验证中单个文件的结果。"""
    filename: str = Field(..., description="文件名")
    success: bool = Field(..., description="是否成功提取到水印")
    employee_id: str = Field(default="", description="提取到的员工 ID")
    matched: bool = Field(default=False, description="是否与预期 ID 匹配")
    message: str = Field(default="", description="结果描述")


class VerifyBatchResponse(BaseModel):
    """批量验证响应。"""
    results: list[VerifyBatchItem] = Field(default_factory=list)
    total: int = Field(..., description="文件总数")
    passed: int = Field(..., description="验证通过数")


# ========== 任务状态 ==========

class TaskStatus(str, Enum):
    """任务状态枚举。"""
    PENDING = "pending"          # 等待处理
    PROCESSING = "processing"    # 处理中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"            # 失败


class TaskResponse(BaseModel):
    """任务状态响应。"""
    task_id: str = Field(..., description="任务 ID")
    status: TaskStatus = Field(..., description="任务状态")
    progress: int = Field(default=0, ge=0, le=100, description="进度 0-100")
    message: str = Field(default="", description="状态描述")
    filename: str = Field(default="", description="关联的文件名")
    created_at: str = Field(default="", description="创建时间 ISO 格式")


# ========== 系统配置 ==========

class ConfigResponse(BaseModel):
    """系统配置响应。"""
    supported_extensions: list[str] = Field(default_factory=list)
    max_file_size_mb: int = Field(default=500)
    strengths: list[str] = Field(default_factory=list)


# ========== 历史记录 ==========

class HistoryItem(BaseModel):
    """操作历史条目。"""
    task_id: str = Field(..., description="任务 ID")
    operation: str = Field(..., description="操作类型: embed/extract/verify")
    filename: str = Field(..., description="文件名")
    status: str = Field(..., description="任务最终状态")
    employee_id: str = Field(default="", description="关联员工 ID")
    created_at: str = Field(..., description="创建时间")
    message: str = Field(default="", description="结果描述")


class HistoryResponse(BaseModel):
    """历史记录分页响应。"""
    items: list[HistoryItem] = Field(default_factory=list)
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页条数")
