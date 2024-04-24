from typing import Any

from fastapi import APIRouter, Query

# from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import col, select

from app.core.base import PagingQueryBase
from app.core.config import base_path
from app.depends import AsyncSessionDep
from app.models.tasks_model import TaskTemplates
from app.utils.files_tools import remove_dir

from . import templates_crud as crud
from . import templates_schema as schema

router = APIRouter()


@router.get(
    "/get/{tid}", summary="查询任务模版", response_model=schema.GetTemplateResponse
)
async def tasks_get_template(session: AsyncSessionDep, tid: str) -> Any:
    """
    查询任务模版
    """
    response = schema.GetTemplateResponse
    # 判断任务模版是否存在
    stmt = select(TaskTemplates).where((col(TaskTemplates.id) == tid))
    template = (await session.exec(stmt)).one_or_none()
    if not template:
        return response(message=f"对象 {tid} 不存在").fail()
    return response(message="查询成功", data=template).success()


@router.post(
    "/add", summary="创建任务模版", response_model=schema.CreateTemplateResponse
)
async def tasks_add_template(
    session: AsyncSessionDep, template_create: schema.CreateTemplate
) -> Any:
    """
    创建任务模版
    """
    response = schema.CreateTemplateResponse
    # 判断任务模版是否存在
    stmt = select(TaskTemplates).where(
        (col(TaskTemplates.name) == template_create.name)
    )
    template = (await session.exec(stmt)).one_or_none()
    if template:
        return response(message=f"对象 {template_create.name} 已存在").fail()
    db_template = await crud.create_template(session, template_create)
    return response(message="创建成功", data=db_template).success()


@router.get(
    "/query", summary="过滤任务模版", response_model=schema.TemplateQueryResponse
)
async def tasks_template_query(
    session: AsyncSessionDep,
    name: str = Query(None),
    task_type: str = Query(None),
    is_all: bool = False,
    limit: int = 12,
    page: int = 1,
) -> Any:
    """
    过滤模版
    """
    response = schema.TemplateQueryResponse
    # 查询全部
    if is_all:
        stmt = select(TaskTemplates).order_by(-TaskTemplates.create_at)
        if task_type:
            stmt = stmt.where(col(TaskTemplates.task_type) == task_type)
        result = (await session.exec(stmt)).all()
        data = schema.TemplateQueryResult(result=result)
        return response(message="查询成功", data=data).success()
    # 序列化查询参数
    query: dict[str, Any] = {}
    if name:
        query.setdefault("name", name)
    if task_type:
        query.setdefault("task_type", task_type)
    # 查询结果
    order_by = -TaskTemplates.create_at
    paging_query = PagingQueryBase(
        query, order_by, limit, page, TaskTemplates, schema.TemplateQueryResult
    )
    if query.get("name"):
        fitter = col(TaskTemplates.name).like(f"%{name}%")
        del query["name"]
        result = await paging_query.fuzzy_query(session, fitter, query)
    else:
        result = await paging_query.query(session)
    return response(message="查询成功", data=result).success()


@router.delete(
    "/del/{tid}", summary="删除任务模版", response_model=schema.DeleteTemplateResponse
)
async def tasks_del_template(session: AsyncSessionDep, tid: str) -> Any:
    response = schema.DeleteTemplateResponse
    template = await session.get(TaskTemplates, tid)
    if not template:
        return response(message="未查询到对象").fail()
    await session.delete(template)
    await session.commit()
    remove_dir(f"{base_path.tasks_templates_path}/{str(template.id)}")
    return response(message="删除成功", data={"id": template.id}).success()


@router.patch(
    "/set/{tid}", summary="更新任务模版", response_model=schema.UpdateTemplateResponse
)
async def tasks_set_template(
    session: AsyncSessionDep, tid: str, update_content: schema.UpdateTemplate
) -> Any:
    response = schema.UpdateTemplateResponse
    template = await session.get(TaskTemplates, tid)
    if not template:
        return response(message="未查询到对象").fail()
    update_data = update_content.model_dump(exclude_unset=True)
    template.sqlmodel_update(update_data)
    session.add(template)
    await session.commit()
    await session.refresh(template)
    return response(message="更新成功", data=template).success()


@router.patch(
    "/set_files/{tid}",
    summary="更新任务模版文件",
    response_model=schema.GetTemplateResponse,
)
async def tasks_set_template_files(
    session: AsyncSessionDep, tid: str, file_content: schema.UpdateTemplateFiles
) -> Any:
    response = schema.GetTemplateResponse
    template = await session.get(TaskTemplates, tid)
    if not template:
        return response(message="未查询到对象").fail()
    await crud.update_template_files(file_content)
    return response(message="更新成功", data=template).success()
