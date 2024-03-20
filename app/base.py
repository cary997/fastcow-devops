import time
from typing import Dict, List, Mapping, Optional, TypeVar, Union

from fastapi import BackgroundTasks
from fastapi.encoders import jsonable_encoder
from sqlmodel import BIGINT, Field, SQLModel
from starlette.responses import JSONResponse

T = TypeVar("T", Dict, List, SQLModel)


class ModelBase(SQLModel):
    """
    抽象模型
    """

    id: Optional[int] = Field(sa_type=BIGINT, default=None, primary_key=True)
    create_at: Optional[int] = Field(
        sa_type=BIGINT, default_factory=lambda: int(time.time())
    )
    update_at: Optional[int] = Field(
        sa_type=BIGINT,
        default_factory=lambda: int(time.time()),
        sa_column_kwargs={"onupdate": int(time.time())},
    )


class ResponseBase(SQLModel):
    """
    基础响应模型
    """

    code: Optional[int] = Field(default=1, description="成功1失败0")
    message: Optional[str] = Field(default=None, description="提示信息")
    data: Optional[Union[Dict, List, SQLModel]] = Field(
        default=None, description="响应数据"
    )

    def success(
        self,
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTasks | None = None,
        **kwags,
    ) -> JSONResponse:
        """成功返回格式"""
        if self.data is None:
            self.data = {}
        content = jsonable_encoder(
            {"code": 1, "message": self.message, "data": self.data, **kwags}
        )

        return JSONResponse(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
        )

    def fail(
        self,
        status_code: int = 400,
        headers: Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTasks | None = None,
    ) -> JSONResponse:
        """失败返回格式"""
        if self.data is None:
            self.data = {}
        content = jsonable_encoder(
            {"code": 0, "message": self.message, "data": self.data}
        )
        return JSONResponse(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
        )


if __name__ == "__main__":
    a = ResponseBase
    print(a(message="hello world", data=[]).fail())
