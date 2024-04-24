import math
import time
from typing import Any, Mapping, Optional, Type, TypeVar

from fastapi import BackgroundTasks, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy import func
from sqlmodel import BIGINT, Field, SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.responses import JSONResponse


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


T = TypeVar("T")


class ResponseBase(SQLModel):
    """
    基础响应模型
    """

    code: Optional[int] = Field(default=1, description="成功1失败0")
    message: Optional[str] = Field(default=None, description="提示信息")
    data: Optional[T] = Field(default=None, description="响应数据")

    def success(
        self,
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTasks | None = None,
        **kwargs,
    ) -> JSONResponse:
        """成功返回格式"""
        if self.data is None:
            self.data = {}
        content = jsonable_encoder(
            {"code": 1, "message": self.message, "data": self.data, **kwargs}
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


class PagingQueryBaseModel(BaseModel):
    """
    分页查询基础模型
    """

    result: Optional[list] = None
    total: Optional[int] = None
    page_total: Optional[int] = None
    page: Optional[int] = None
    limit: Optional[int] = None


QueryModelT = TypeVar("QueryModelT", bound=BaseModel)
ResultModelT = TypeVar("ResultModelT", bound=BaseModel)


class PagingQueryBase:
    """
    分页查询基础模型
    """

    def __init__(
        self,
        query_kwargs: dict[str, Any],
        order_by: Any,
        limit: int,
        page: int,
        query_model: Type[QueryModelT],
        result_model: Type[ResultModelT],
    ):
        self.query_kwargs = query_kwargs
        self.order_by = order_by
        self.limit = limit
        self.page = page
        self.query_model = query_model
        self.result_model = result_model
        self.stmt = select(query_model)
        self.total_stmt = select(func.count()).select_from(query_model)

    async def get_result(
        self, session: AsyncSession, stmt: Any, total_stmt: Any
    ) -> PagingQueryBaseModel:
        query_data = (
            await session.exec(
                stmt.limit(self.limit)
                .offset(self.limit * (self.page - 1))
                .order_by(self.order_by)
            )
        ).all()
        query_total = (await session.exec(total_stmt)).one()
        if not query_total:
            return self.result_model(
                result=[],
                total=query_total,
                page_total=0,
                page=0,
                limit=0,
            )
        # 分页总数
        page_total = math.ceil(int(query_total) / self.limit)
        if self.page > page_total:
            raise HTTPException(status_code=400, detail="输入页数大于分页总数!")
        result = self.result_model(
            result=query_data,
            total=query_total,
            page_total=page_total,
            page=self.page,
            limit=self.limit,
        )
        return result

    async def query(self, session: AsyncSession, select_where: Optional[Any] = None):
        # 查询结果
        stmt = self.stmt.filter_by(**self.query_kwargs)
        total_stmt = self.total_stmt.filter_by(**self.query_kwargs)
        if select_where is not None:
            stmt = stmt.where(select_where)
            total_stmt = total_stmt.where(select_where)
        result = await self.get_result(session, stmt, total_stmt)
        return result

    async def fuzzy_query(
        self, session: AsyncSession, filters: Any, filter_by: Optional[dict] = None
    ):
        stmt = self.stmt
        total_stmt = self.total_stmt
        if filter_by is not None:
            stmt = stmt.filter_by(**filter_by)
            total_stmt = total_stmt.filter_by(**filter_by)
        stmt = stmt.filter(filters)
        total_stmt = total_stmt.filter(filters)
        result = await self.get_result(session, stmt, total_stmt)
        return result
