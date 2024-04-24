import os
import signal
import time
import uuid
from pathlib import Path
from typing import Any

import aiofiles
from fastapi import APIRouter, Query, Request
from sqlmodel import col, select

from app.core.base import PagingQueryBase, ResponseBase
from app.core.config import base_path
from app.depends import AsyncSessionDep, SessionDep
from app.ext.ansible_tsk.runner import (
    RunConf,
    TasksRunConfig,
    create_task_record,
    parse_task_conf,
)
from app.ext.ansible_tsk.tasks import asb_temp_task
from app.models.tasks_model import TasksHistory
from app.tasks import celery
from app.utils.files_tools import remove_dir

from . import execution_schema as schemas

router = APIRouter()


@router.get(
    "/get/{tid}", summary="查询任务历史", response_model=schemas.GetHistoryResponse
)
async def tasks_history_get(session: AsyncSessionDep, tid: str) -> Any:
    """
    查询任务历史
    """
    response = schemas.GetHistoryResponse
    task_record = await session.get(TasksHistory, tid)
    if not task_record:
        return response(message=f"对象 {tid} 不存在").fail()
    return response(message="查询成功", data=task_record).success()


@router.post("/run", summary="执行任务", response_model=schemas.TasksRunResponse)
async def tasks_exec_run(
    session: SessionDep, req: Request, run_conf: TasksRunConfig
) -> Any:
    """
    执行任务
    """
    response = schemas.TasksRunResponse
    if not run_conf.ident:
        task_id = str(uuid.uuid4())
        run_conf.ident = task_id
    run_conf = parse_task_conf(run_conf)
    run_conf.task_queue_type = "asb_temp_task"
    task_record = create_task_record(
        session=session, username=req.state.username, run_conf=run_conf
    )
    asb_temp_task.apply_async(
        task_id=run_conf.ident,
        kwargs=run_conf.model_dump(),
        time_limit=run_conf.timeout,
    )
    return response(message="任务已添加至队列", data=task_record).success()


@router.post("/check", summary="检查配置", response_model=schemas.CheckConfigResponse)
async def tasks_exec_check(run_conf: TasksRunConfig) -> Any:
    if not run_conf.ident:
        task_id = str(uuid.uuid4())
        run_conf.ident = task_id
    run_conf = parse_task_conf(run_conf)
    run_conf.task_queue_type = "asb_temp_task"
    run_config = RunConf.model_validate(run_conf.model_dump())
    res = run_config.config_check()
    data = schemas.CheckConfigResult.validate(res)
    return schemas.CheckConfigResponse(message="检查完成", data=data).success()


@router.post("/revoke/{tid}", summary="任务取消", response_model=ResponseBase)
async def tasks_exec_revoke(tid: str) -> Any:
    result = celery.AsyncResult(tid)
    if result.state in ["PENDING", "STARTED", "RETRY"]:
        result.revoke(terminate=True, signal=signal.SIGTERM)
    else:
        return ResponseBase(message="任务状态不支持取消").fail()
    return ResponseBase(message=f"{tid} 任务正在取消 请尝试刷新页面").success()


@router.delete(
    "/del",
    summary="删除任务历史",
    response_model=schemas.DeleteTasksHistoryResponse,
)
async def tasks_exec_del(
    session: AsyncSessionDep, history_id: schemas.DeleteListId
) -> Any:
    """
    删除任务记录
    """
    response = schemas.DeleteTasksHistoryResponse
    task_records = (
        await session.exec(
            select(TasksHistory).where(col(TasksHistory.id).in_(history_id.id_list))
        )
    ).all()
    if len(task_records) == 0:
        return response(message="未查询到记录").fail()
    res_list = []
    for task_record in task_records:
        task_kwargs = task_record.task_kwargs
        private_data_dir = task_kwargs.get("private_data_dir")
        if private_data_dir:
            remove_dir(private_data_dir)
        del_res = schemas.DeleteTasksHistoryResult(
            id=task_record.id,
            task_id=task_record.task_id,
            private_data_dir=private_data_dir,
        )
        await session.delete(task_record)
        res_list.append(del_res)
    await session.commit()
    return response(message="删除成功", data=res_list).success()


@router.get(
    "/query", summary="过滤任务历史", response_model=schemas.TasksHistoryQueryResponse
)
async def tasks_history_query(
    session: AsyncSessionDep,
    task_name: str = Query(None),
    task_status: str = Query(None),
    task_type: str = Query(None),
    task_queue_type: str = Query(None),
    task_scheduled_name: str = Query(None),
    limit: int = 10,
    page: int = 1,
) -> Any:
    """
    过滤任务历史
    """
    response = schemas.TasksHistoryQueryResponse
    # 序列化查询参数
    query: dict[str, Any] = {}
    if task_name:
        query.setdefault("task_name", task_name)
    if task_type:
        query.setdefault("task_type", task_type)
    if task_status:
        query.setdefault("task_status", task_status)
    if task_queue_type:
        query.setdefault("task_queue_type", task_queue_type)
    if task_scheduled_name:
        query.setdefault("task_scheduled_name", task_scheduled_name)
    order_by = -TasksHistory.task_start_time
    paging_query = PagingQueryBase(
        query, order_by, limit, page, TasksHistory, schemas.TasksHistoryQueryResult
    )
    if task_name:
        fitter = col(TasksHistory.task_name).like(f"%{task_name}%")
        del query["task_name"]
        result = await paging_query.fuzzy_query(session, fitter, query)
    else:
        result = await paging_query.query(session)
    return response(message="查询成功", data=result).success()


@router.get(
    "/read_stdout",
    summary="读取任务输出",
    response_model=schemas.GetTaskStdoutResponse,
)
async def get_task_stdout(task_id: str = Query(), private_dir: str = Query()) -> Any:
    response = schemas.GetTaskStdoutResponse
    private_path = Path(os.path.join(base_path.tasks_meta_path, private_dir))
    if not os.path.exists(private_path):
        return response(message="未查询到任务输出", data=None).fail()
    artifact_path = os.path.join(private_path, "artifacts", task_id, "stdout")
    async with aiofiles.open(artifact_path, "rb") as file:
        content = await file.read()
        await file.close()
    return response(message="读取文件成功", data=content).success()


@router.get(
    "/history_statistics/{periodic}",
    summary="任务历史统计",
    response_model=schemas.HistoryStatisticsResponse,
)
async def task_history_statistics(session: AsyncSessionDep, periodic: int):
    base_periodic = 60 * 60 * 24 * periodic
    time_now = int(time.time())
    time_start = time_now - base_periodic
    periodic_tasks_all = (
        await session.exec(
            select(TasksHistory).where(TasksHistory.task_start_time >= time_start)
        )
    ).all()
    exec_count = len(periodic_tasks_all)
    exec_success_count = 0
    exec_fail_count = 0
    exec_running_count = 0
    exec_duration_max = 0
    exec_duration_min = 0
    exec_duration_avg_list = []
    exec_duration_avg = 0
    for task in periodic_tasks_all:
        task_duration = task.task_duration
        if not task_duration:
            task_duration = 0
        else:
            exec_duration_avg_list.append(task_duration)
        if exec_duration_min == 0:
            exec_duration_min = task_duration
        if task_duration > exec_duration_max:
            exec_duration_max = task_duration
        if task_duration < exec_duration_min:
            exec_duration_min = task_duration
        if task.task_status == "successful":
            exec_success_count += 1
        elif task.task_status not in ["successful", "starting", "running"]:
            exec_fail_count += 1
        elif task.task_status in ["starting", "running"]:
            exec_running_count += 1
    if exec_duration_avg_list:
        exec_duration_avg = int(
            sum(exec_duration_avg_list) / len(exec_duration_avg_list)
        )
    result = schemas.HistoryStatisticsResult(
        exec_count=exec_count,
        exec_success_count=exec_success_count,
        exec_fail_count=exec_fail_count,
        exec_running_count=exec_running_count,
        exec_duration_max=exec_duration_max,
        exec_duration_min=exec_duration_min,
        exec_duration_avg=exec_duration_avg,
    )
    return schemas.HistoryStatisticsResponse(message="查询成功", data=result).success()
