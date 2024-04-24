from typing import Any

from fastapi import APIRouter, Query, Request
from sqlmodel import col, select

from app.core.base import PagingQueryBase
from app.depends import AsyncSessionDep
from app.ext.sqlmodel_celery_beat.models import PeriodicTask

from . import scheduled_crud as crud
from . import scheduled_schema as schemas

router = APIRouter()


@router.post(
    "/add", summary="创建定时任务", response_model=schemas.CreateScheduledTaskResponse
)
async def task_scheduled_add(
    session: AsyncSessionDep,
    req: Request,
    create_scheduled: schemas.CreateScheduledTask,
) -> Any:
    response = schemas.CreateScheduledTaskResponse
    periodic_task, schedule = crud.parse_scheduled_create_body(
        create_scheduled, req.state.username
    )
    db_periodic_task = (
        await session.exec(
            select(PeriodicTask).where(PeriodicTask.name == periodic_task.name)
        )
    ).one_or_none()
    if db_periodic_task:
        return response(message=f"任务名重复 ${periodic_task.name}").fail()
    db_periodic_task = await crud.create_periodic_task(session, periodic_task, schedule)
    return response(message="添加成功", data=db_periodic_task).success()


@router.delete(
    path="/del/{sid}",
    summary="删除定时任务",
    response_model=schemas.DeleteScheduledTaskResponse,
)
async def task_scheduled_del(session: AsyncSessionDep, sid: int) -> Any:
    response = schemas.DeleteScheduledTaskResponse
    periodic_task = await session.get(PeriodicTask, sid)
    if not periodic_task:
        return response(message="任务不存在").fail()
    periodic_task = await crud.delete_periodic_scheduler(session, periodic_task)
    await session.delete(periodic_task)
    await session.commit()
    return response(message="删除成功", data={"id": sid}).success()


@router.put(
    path="/set/{sid}",
    summary="更新定时任务",
    response_model=schemas.UpdateScheduledTaskResponse,
)
async def task_scheduled_set(
    session: AsyncSessionDep,
    req: Request,
    sid: int,
    update_scheduled: schemas.UpdateScheduledTask,
) -> Any:
    db_periodic_task = await session.get(PeriodicTask, sid)
    response = schemas.UpdateScheduledTaskResponse
    if not db_periodic_task:
        return response(message="任务不存在").fail()
    periodic_task, schedule = crud.parse_scheduled_create_body(
        update_scheduled, req.state.username
    )
    db_periodic_task = await crud.update_periodic_task(
        session, db_periodic_task, periodic_task, schedule
    )
    return response(message="更新成功", data=db_periodic_task).success()


@router.patch(
    path="/sys_set/{sid}",
    summary="更新系统内置定时任务",
    response_model=schemas.UpdateScheduledTaskResponse,
)
async def task_scheduled_sys_set(
    session: AsyncSessionDep,
    req: Request,
    sid: int,
    update_scheduled: schemas.UpdateSysScheduledTask,
) -> Any:
    db_periodic_task = await session.get(PeriodicTask, sid)
    response = schemas.UpdateScheduledTaskResponse
    if not db_periodic_task:
        return response(message="任务不存在").fail()
    db_periodic_task = await crud.update_sys_periodic_task(
        session, db_periodic_task, update_scheduled, req.state.username
    )
    return response(message="更新成功", data=db_periodic_task).success()


@router.get(
    "/query", summary="过滤定时任务", response_model=schemas.ScheduledQueryResponse
)
async def tasks_scheduled_query(
    session: AsyncSessionDep,
    name: str = Query(None),
    types: str = Query("interval"),
    task_type: str = Query(None),
    enabled: bool = Query(None),
    one_off: bool = Query(None),
    limit: int = 10,
    page: int = 1,
) -> Any:
    response = schemas.ScheduledQueryResponse
    # 序列化查询参数
    query: dict[str, Any] = {}
    if enabled is not None:
        query.setdefault("enabled", enabled)
    if types:
        query.setdefault("types", types)
    if task_type:
        query.setdefault("task_type", task_type)
    if one_off is not None:
        query.setdefault("one_off", one_off)
    order_by = -PeriodicTask.create_at
    paging_query = PagingQueryBase(
        query, order_by, limit, page, PeriodicTask, schemas.ScheduledQueryResult
    )
    if name:
        fitter = col(PeriodicTask.name).like(f"%{name}%")
        del query["types"]
        result = await paging_query.fuzzy_query(session, fitter, query)
    else:
        result = await paging_query.query(session)
    return response(message="查询成功", data=result).success()
