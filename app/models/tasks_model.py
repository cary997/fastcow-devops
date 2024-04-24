import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

import sqlalchemy as sa
from celery import states
from pydantic import UUID4, computed_field
from sqlalchemy.types import PickleType
from sqlmodel import JSON, TEXT, Field, SQLModel

from app.core.base import ModelBase
from app.utils.db_tools import generate_id


class TaskMeta(SQLModel, table=True):
    """
    任务执行结果信息
    查询使用
    """

    __tablename__ = "tasks_meta"

    id: int = Field(
        sa_column=sa.Column(
            sa.Integer,
            sa.Sequence("task_id_sequence"),
            primary_key=True,
            autoincrement=True,
        )
    )
    task_id: str = Field(sa_column=sa.Column(sa.String(155), unique=True))
    status: str = Field(sa_column=sa.Column(sa.String(50), default=states.PENDING))
    result: str = Field(sa_column=sa.Column(PickleType, nullable=True))
    date_done: datetime = Field(
        sa_column=sa.Column(
            sa.DateTime,
            default=datetime.now,
            onupdate=datetime.now,
            nullable=True,
        )
    )
    traceback: str = Field(sa_column=sa.Column(sa.Text, nullable=True))
    name: str = Field(sa_column=sa.Column(sa.String(155), nullable=True))
    args: str = Field(sa_column=sa.Column(sa.LargeBinary, nullable=True))
    kwargs: str = Field(sa_column=sa.Column(sa.LargeBinary, nullable=True))
    worker: str = Field(sa_column=sa.Column(sa.String(155), nullable=True))
    retries: int = Field(sa_column=sa.Column(sa.Integer, nullable=True))
    queue: str = Field(sa_column=sa.Column(sa.String(155), nullable=True))


class GroupTaskMeta(SQLModel, table=True):
    """
    任务组执行结果信息
    查询使用
    """

    __tablename__ = "tasks_group_meta"

    id: int = Field(
        sa_column=sa.Column(
            sa.Integer,
            sa.Sequence("taskset_id_sequence"),
            autoincrement=True,
            primary_key=True,
        )
    )
    taskset_id: str = Field(sa_column=sa.Column(sa.String(155), unique=True))
    result: str = Field(sa_column=sa.Column(PickleType, nullable=True))
    date_done: datetime = Field(
        sa_column=sa.Column(sa.DateTime, default=datetime.now, nullable=True)
    )


class TaskType(str,Enum):
    """
    任务类型
    """
    adhoc = "Ad-Hoc"
    playbook = "Playbook"
    file_store = "FileStore"
    sys_api = "SysApi"

class TaskTemplatesBase(SQLModel):
    """
    任务模版基础信息
    """

    name: str = Field(default=..., unique=True, max_length=16, description="模版名称")
    task_type: TaskType = Field(default=TaskType.playbook, description="任务类型")
    desc: Optional[str] = Field(default=None, description="任务描述", nullable=True)


class TaskTemplates(TaskTemplatesBase, ModelBase, table=True):
    """
    任务模版表信息
    """

    __tablename__ = "tasks_templates"
    id: UUID4 = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )


class TasksHistoryBase(SQLModel):
    """
    任务历史信息
    """

    task_id: str = Field(default=..., unique=True, description="任务id")
    task_type: TaskType = Field(default=TaskType.adhoc, description="任务类型")
    task_name: str = Field(default=..., description="任务名称")
    task_queue_type: str = Field(default=None, description="任务队列类型")
    task_kwargs: dict = Field(default=..., sa_type=JSON, description="任务参数")
    task_rc: Optional[int] = Field(default=None, description="任务返回码")
    task_status: Optional[str] = Field(default=None, description="任务状态")
    task_error: Optional[str] = Field(
        default=None, sa_type=TEXT, description="任务错误信息"
    )
    task_start_time: Optional[int] = Field(default=None, description="任务开始时间")
    task_end_time: Optional[int] = Field(default=None, description="任务结束时间")
    task_template_id: Optional[str] = Field(default=None, description="任务模版ID")
    task_template_name: Optional[str] = Field(default=None, description="任务模版名称")
    exec_user: Optional[str] = Field(default=None, description="执行用户")
    exec_worker: Optional[str] = Field(default=None, description="执行节点")
    task_scheduled_name: Optional[str] = Field(default=None, description="任务计划名称")

    @computed_field
    def task_duration(self) -> Optional[int]:
        """
        任务执行时长
        """
        if self.task_end_time is None or self.task_start_time is None:
            return None
        duration = self.task_end_time - self.task_start_time
        return duration


class TasksHistory(TasksHistoryBase, ModelBase, table=True):
    """
    任务历史表信息
    """

    __tablename__ = "tasks_history"
