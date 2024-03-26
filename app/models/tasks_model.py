from datetime import datetime

import sqlalchemy as sa
from celery import states
from sqlalchemy.types import PickleType
from sqlmodel import Field, SQLModel


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
            default=datetime.utcnow,
            onupdate=datetime.utcnow,
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
        sa_column=sa.Column(sa.DateTime, default=datetime.utcnow, nullable=True)
    )
