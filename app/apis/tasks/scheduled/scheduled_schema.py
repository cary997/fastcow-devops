from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Json
from sqlmodel import JSON, Field

from app.core.base import PagingQueryBaseModel, ResponseBase
from app.core.config import settings
from app.ext.ansible_tsk.runner import TasksRunConfig
from app.ext.sqlmodel_celery_beat.models import (
    IntervalPeriod,
    PeriodicTask,
    ScheduledType,
)


class PeriodicTaskBase(BaseModel):
    """
    定时任务基类
    """

    types: ScheduledType = Field(default=ScheduledType.interval)
    headers: Optional[Json] = Field(default={})
    priority: Optional[int] = Field(default=None)
    expire_seconds: Optional[int] = Field(default=None)
    one_off: bool = Field(default=False)
    enabled: bool = Field(default=True)
    description: Optional[str] = Field(default=None, max_length=128)


class CrontabScheduleBase(PeriodicTaskBase):
    """
    定时任务基类
    """

    minute: Optional[str] = Field(max_length=60 * 4, default="*")
    hour: Optional[str] = Field(max_length=24 * 4, default="*")
    day_of_week: Optional[str] = Field(max_length=64, default="*")
    day_of_month: Optional[str] = Field(max_length=31 * 4, default="*")
    month_of_year: Optional[str] = Field(max_length=64, default="*")
    timezone: Optional[str] = Field(max_length=64, default=settings.SYS_TIMEZONE)


class IntervalScheduleBase(PeriodicTaskBase):
    """Schedule executing every n seconds, minutes, hours or days."""

    every: Optional[int] = 0
    period: IntervalPeriod = Field(default=IntervalPeriod.SECONDS)


class ScheduledConfig(CrontabScheduleBase, IntervalScheduleBase):
    """
    scheduled配置
    """


class CreateScheduledTask(BaseModel):
    """
    创建定时任务
    """

    scheduled_config: ScheduledConfig
    task_run_config: TasksRunConfig


class UpdateScheduledTask(CreateScheduledTask):
    """
    更新定时任务
    """


class UpdateSysScheduledTask(BaseModel):
    """
    更新系统内置定时任务
    """

    scheduled_config: ScheduledConfig
    kwargs: Optional[Json] = Field(default=None)


class CreateScheduledTaskResponse(ResponseBase):
    data: Optional[PeriodicTask] = None


class ScheduledQueryResult(PagingQueryBaseModel):
    """
    定时任务过滤结果
    """

    result: Optional[list[PeriodicTask]] = None


class ScheduledQueryResponse(ResponseBase):
    """
    定时任务过滤响应
    """

    data: ScheduledQueryResult


class DeleteScheduledTaskResponse(ResponseBase):
    """
    scheduled任务删除响应
    """

    data: Optional[dict[str, int]] = None


class UpdateScheduledTaskResponse(CreateScheduledTaskResponse):
    """
    scheduled任务更新响应
    """
