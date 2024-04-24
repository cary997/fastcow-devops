from typing import Tuple, Union

from fastapi.exceptions import HTTPException, RequestValidationError
from pydantic import ValidationError
from sqlalchemy.orm.attributes import flag_modified
from sqlmodel.ext.asyncio.session import AsyncSession

from app.ext.sqlmodel_celery_beat.models import (
    CrontabSchedule,
    IntervalSchedule,
    PeriodicTask,
    ScheduledType,
)

from . import scheduled_schema as schemas


def get_Schedule(
    scheduled_config: schemas.ScheduledConfig,
) -> CrontabSchedule | IntervalSchedule:
    """
    解析定时配置
    """
    if scheduled_config.types == ScheduledType.crontab:
        return CrontabSchedule(
            minute=scheduled_config.minute,
            hour=scheduled_config.hour,
            day_of_week=scheduled_config.day_of_week,
            day_of_month=scheduled_config.day_of_month,
            month_of_year=scheduled_config.month_of_year,
            timezone=scheduled_config.timezone,
        )
    elif scheduled_config.types == ScheduledType.interval:
        return IntervalSchedule(
            every=scheduled_config.every,
            period=scheduled_config.period,
        )
    else:
        raise RequestValidationError("定时任务类型错误")


def parse_scheduled_create_body(
    body: schemas.CreateScheduledTask,
    username: str,
) -> Tuple[PeriodicTask, Union[CrontabSchedule, IntervalSchedule]]:
    """
    解析创建定时任务请求
    """
    scheduled_config = body.scheduled_config
    task_run_config = body.task_run_config
    if scheduled_config.headers == "{}" or not scheduled_config.headers:
        scheduled_config.headers = {}
    periodic_task = PeriodicTask(
        name=task_run_config.task_name,
        task="tasks.asb_scheduled_task",
        types=scheduled_config.types,
        task_type=task_run_config.task_type,
        kwargs=task_run_config.model_dump(exclude_none=True),
        priority=scheduled_config.priority,
        expire_seconds=scheduled_config.expire_seconds,
        queue="asb_scheduled_task",
        exchange="ansible",
        routing_key="ansible.scheduled",
        one_off=scheduled_config.one_off,
        enabled=scheduled_config.enabled,
        description=scheduled_config.description,
        headers=scheduled_config.headers,
        user_by=username,
    )

    schedule = get_Schedule(scheduled_config)
    return periodic_task, schedule


async def create_periodic_task(
    session: AsyncSession,
    periodic_task: PeriodicTask,
    schedule: Union[CrontabSchedule, IntervalSchedule],
) -> PeriodicTask:
    """
    创建定时任务
    """
    if periodic_task.types == ScheduledType.crontab:
        periodic_task.crontab = schedule
    if periodic_task.types == ScheduledType.interval:
        periodic_task.interval = schedule
    try:
        session.add(schedule)
        session.add(periodic_task)
        await session.commit()
        return periodic_task
    except Exception as e:
        await session.rollback()
        raise e


async def delete_periodic_scheduler(
    session: AsyncSession,
    periodic_task: PeriodicTask,
    scheduler: Union[CrontabSchedule, IntervalSchedule] = None,
):
    """
    删除定时任务 关联的scheduler
    """
    if not scheduler:
        scheduler = periodic_task.scheduled
    try:
        await session.delete(scheduler)
        await session.commit()
        await session.refresh(periodic_task)
        return periodic_task
    except Exception as e:
        await session.rollback()
        raise e


async def update_periodic_task(
    session: AsyncSession,
    db_periodic_task: PeriodicTask,
    periodic_task: PeriodicTask,
    schedule: Union[CrontabSchedule, IntervalSchedule],
) -> PeriodicTask:
    """
    更新定时任务
    """
    try:
        db_scheduler = db_periodic_task.scheduled
        if periodic_task.types == db_periodic_task.types:
            db_scheduler.sqlmodel_update(
                schedule.model_dump(exclude_none=True, exclude_unset=True)
            )
        else:
            db_periodic_task = await delete_periodic_scheduler(
                session, db_periodic_task, db_scheduler
            )
            if periodic_task.types == ScheduledType.crontab:
                db_periodic_task.crontab = schedule
                db_scheduler = schedule
            if periodic_task.types == ScheduledType.interval:
                db_periodic_task.interval = schedule
                db_scheduler = schedule
        db_periodic_task.sqlmodel_update(
            periodic_task.model_dump(
                exclude_none=True,
                exclude_unset=True,
                exclude={"scheduled", "schedule_str"},
            )
        )
    except ValidationError as e:
        raise RequestValidationError(str(e))
    except ValueError as e:
        raise HTTPException(status_code=418, detail=str(e))
    try:
        if periodic_task.headers:
            flag_modified(db_periodic_task, "headers")
        flag_modified(db_periodic_task, "kwargs")
        session.add(db_scheduler)
        session.add(db_periodic_task)
        await session.commit()
        await session.refresh(db_periodic_task)
        return db_periodic_task
    except ValidationError as e:
        raise RequestValidationError(str(e))
    except Exception as e:
        await session.rollback()
        raise e


async def update_sys_periodic_task(
    session: AsyncSession,
    db_periodic_task: PeriodicTask,
    update_scheduled: schemas.UpdateSysScheduledTask,
    username: str,
) -> PeriodicTask:
    """
    更新系统定时任务
    """
    scheduled_config = update_scheduled.scheduled_config
    schedule = None
    if db_periodic_task.interval_id:
        schedule = IntervalSchedule(
            every=scheduled_config.every,
            period=scheduled_config.period,
        )
    elif db_periodic_task.crontab_id:
        schedule = CrontabSchedule(
            minute=scheduled_config.minute,
            hour=scheduled_config.hour,
            day_of_week=scheduled_config.day_of_week,
            day_of_month=scheduled_config.day_of_month,
            month_of_year=scheduled_config.month_of_year,
            timezone=scheduled_config.timezone,
        )

    include_fields = set(schemas.PeriodicTaskBase.model_fields.keys())
    db_periodic_task.sqlmodel_update(
        scheduled_config.model_dump(
            exclude_none=True,
            exclude_unset=True,
            include=include_fields,
        )
    )
    db_periodic_task.kwargs = update_scheduled.kwargs
    db_periodic_task.user_by = username
    try:
        if schedule:
            db_scheduler = db_periodic_task.scheduled
            db_scheduler.sqlmodel_update(
                schedule.model_dump(exclude_none=True, exclude_unset=True)
            )
            session.add(db_scheduler)
        flag_modified(db_periodic_task, "kwargs")
        session.add(db_periodic_task)
        await session.commit()
        await session.refresh(db_periodic_task)
        return db_periodic_task
    except ValidationError as e:
        raise RequestValidationError(str(e))
    except Exception as e:
        await session.rollback()
        raise e
