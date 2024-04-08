import uuid
from datetime import datetime
from enum import Enum, IntEnum
from typing import Optional

import sqlalchemy as sa
from celery import states
from pydantic import UUID4, ConfigDict
from sqlalchemy.types import PickleType
from sqlmodel import JSON, Field, SQLModel

from app.core.base import ModelBase


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


class TaskType(Enum):
    """
    任务类型
    """

    ad_hoc = "Ad-Hoc"
    playbook = "Playbook"
    shell = "Shell"
    python = "Python"


class TaskTemplatesBase(SQLModel):
    """
    任务模版基础信息
    """

    name: str = Field(default=..., unique=True, description="模版名称")
    task_type: TaskType = Field(default=TaskType.ad_hoc, description="任务类型")
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
