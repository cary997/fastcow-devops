from typing import Optional

from pydantic import BaseModel, Field

from app.core.base import ResponseBase


class VerifyFileResult(BaseModel):
    """文件续传校验返回结果"""

    file_hash: str = Field(..., description="文件hash")
    chunks: list[str] = Field(..., description="已经上传的分片")


class VerifyFileResponse(ResponseBase):
    """文件续传校验返回响应"""

    data: VerifyFileResult


class ReadFile(BaseModel):
    """读取文件请求"""

    path: str = Field(..., description="文件路径")


class ReadFileResult(BaseModel):
    """读取文件返回结果"""

    code: bytes | str = Field(..., description="文件内容")
    lang: str = Field(..., description="文件语言")


class ReadFileResponse(ResponseBase):
    """读取文件返回响应"""

    data: Optional[ReadFileResult] = None
