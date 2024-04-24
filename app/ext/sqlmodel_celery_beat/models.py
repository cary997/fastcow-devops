import enum
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional, Union
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from celery import current_app, schedules
from celery.utils.log import get_logger
from cron_descriptor import (
    FormatException,
    MissingFieldException,
    WrongArgumentException,
    get_description,
)
from pydantic import ValidationError, computed_field, field_validator, model_validator
from pydantic_core import InitErrorDetails, PydanticCustomError
from sqlalchemy.event import listen
from sqlmodel import BIGINT, Column, Field, Relationship, Session, SQLModel, select

from app.core.base import ModelBase
from app.core.config import settings

from ...models.tasks_model import TaskType
from .clockedschedule import clocked
from .tzcrontab import TzAwareCrontab
from .util import make_aware, nowfun

logger = get_logger("sqlmodel_celery_beat.models")


def cronexp(field: str) -> str:
    """Representation of cron expression."""
    return field and str(field).replace(" ", "") or "*"


class ModelMixin(ModelBase):
    """Base model mixin"""

    @classmethod
    def create(cls, **kwargs):
        return cls(**kwargs)

    def update(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        return self

    def save(
        self, session: Session, *args, **kwargs
    ):  # pylint: disable=unused-argument
        session.add(self)
        session.commit()


class IntervalPeriod(str, Enum):
    """Enumeration of interval periods."""

    DAYS = "days"
    HOURS = "hours"
    MINUTES = "minutes"
    SECONDS = "seconds"


class IntervalSchedule(ModelMixin, table=True):
    """Schedule executing every n seconds, minutes, hours or days."""

    __tablename__ = "tasks_interval_schedule"
    every: int = 0
    period: IntervalPeriod = Field(
        sa_column=Column(
            sa.Enum(IntervalPeriod, create_constraint=True),
            default=IntervalPeriod.SECONDS,
        )
    )

    periodic_task: Optional["PeriodicTask"] = Relationship(back_populates="interval")

    @property
    def schedule(self):
        return schedules.schedule(timedelta(**{self.period: self.every}), nowfun=nowfun)

    def __str__(self):
        return f"every {self.every} {self.period}"


class SolarEvent(str, Enum):
    """Enumeration of solar events."""

    SUNRISE = "sunrise"
    SUNSET = "sunset"
    DAWN_ASTRONOMICAL = "dawn_astronomical"
    DAWN_CIVIL = "dawn_civil"
    DAWN_NAUTICAL = "dawn_nautical"
    DUSK_ASTRONOMICAL = "dusk_astronomical"
    DUSK_CIVIL = "dusk_civil"
    DUSK_NAUTICAL = "dusk_nautical"
    SOLAR_NOON = "solar_noon"


class SolarSchedule(ModelMixin, table=True):
    """Schedule following astronomical patterns.

    Example: to run every sunrise in New York City:

    # >>> event='sunrise', latitude=40.7128, longitude=74.0060
    """

    __tablename__ = "tasks_solar_schedule"
    event: SolarEvent = Field(
        sa_column=Column(sa.Enum(SolarEvent, create_constraint=True))
    )
    latitude: float
    longitude: float
    periodic_task: Optional["PeriodicTask"] = Relationship(back_populates="solar")

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, v):
        if v < -90 or v > 90:
            raise ValueError("latitude must be between -90 and 90")
        return v

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, v):
        if v < -180 or v > 180:
            raise ValueError("longitude must be between -180 and 180")
        return v

    @property
    def schedule(self):
        return schedules.solar(
            self.event,
            self.latitude,
            self.longitude,
            nowfun=lambda: make_aware(nowfun()),
        )

    def __str__(self):
        return f"{self.get_event_display()} ({self.latitude}, {self.longitude})"


class ClockedSchedule(ModelMixin, table=True):
    """Clocked schedule, run once at a specific time."""

    __tablename__ = "tasks_clocked_schedule"
    clocked_time: datetime = Field(
        sa_column=Column(sa.DateTime(timezone=True), nullable=False)
    )
    periodic_task: Optional["PeriodicTask"] = Relationship(back_populates="clocked")

    def __str__(self):
        return f"{make_aware(self.clocked_time)}"

    @property
    def schedule(self):
        c = clocked(clocked_time=self.clocked_time)
        return c


class CrontabSchedule(ModelMixin, table=True):
    """Timezone Aware Crontab-like schedule.

    Example:  Run every hour at 0 minutes for days of month 10-15:

    # >>> minute="0", hour="*", day_of_week="*",
    # ... day_of_month="10-15", month_of_year="*"
    """

    #
    # The worst case scenario for day of month is a list of all 31 day numbers
    # '[1, 2, ..., 31]' which has a length of 115. Likewise, minute can be
    # 0..59 and hour can be 0..23. Ensure we can accomodate these by allowing
    # 4 chars for each value (what we save on 0-9 accomodates the []).
    # We leave the other fields at their historical length.
    #
    __tablename__ = "tasks_crontab_schedule"
    minute: str = Field(max_length=60 * 4, default="*")
    hour: str = Field(max_length=24 * 4, default="*")
    day_of_week: str = Field(max_length=64, default="*")
    day_of_month: str = Field(max_length=31 * 4, default="*")
    month_of_year: str = Field(max_length=64, default="*")
    timezone: str = Field(max_length=64, default=settings.SYS_TIMEZONE)
    periodic_task: Optional["PeriodicTask"] = Relationship(back_populates="crontab")

    @property
    def human_readable(self):
        cron_expression = (
            "{} {} {} {} {}".format(  # pylint: disable=consider-using-f-string
                cronexp(self.minute),
                cronexp(self.hour),
                cronexp(self.day_of_month),
                cronexp(self.month_of_year),
                cronexp(self.day_of_week),
            )
        )
        try:
            human_readable = get_description(cron_expression)
        except (MissingFieldException, FormatException, WrongArgumentException):
            return f"{cron_expression} {self.timezone}"
        return f"{human_readable} {self.timezone}"

    def __str__(self):
        return "{} {} {} {} {} (m/h/dM/MY/d) {}".format(  # pylint: disable=consider-using-f-string
            cronexp(self.minute),
            cronexp(self.hour),
            cronexp(self.day_of_month),
            cronexp(self.month_of_year),
            cronexp(self.day_of_week),
            str(self.timezone),
        )

    @property
    def schedule(self):
        crontab = schedules.crontab(
            minute=self.minute,
            hour=self.hour,
            day_of_week=self.day_of_week,
            day_of_month=self.day_of_month,
            month_of_year=self.month_of_year,
        )
        if getattr(current_app.conf, "CELERY_BEAT_TZ_AWARE", True):
            crontab = TzAwareCrontab(
                minute=self.minute,
                hour=self.hour,
                day_of_week=self.day_of_week,
                day_of_month=self.day_of_month,
                month_of_year=self.month_of_year,
                tz=ZoneInfo(self.timezone),
            )
        return crontab

    @classmethod
    def from_schedule(cls, session: Session, schedule: schedules.crontab):
        spec = {
            "minute": schedule._orig_minute,  # pylint: disable=protected-access
            "hour": schedule._orig_hour,  # pylint: disable=protected-access
            "day_of_week": schedule._orig_day_of_week,  # pylint: disable=protected-access
            "day_of_month": schedule._orig_day_of_month,  # pylint: disable=protected-access
            "month_of_year": schedule._orig_month_of_year,  # pylint: disable=protected-access
            "timezone": schedule.tz,
        }
        try:
            return session.get(cls, **spec)
        except sa.orm.exc.NoResultFound:
            return cls(**spec)
        except sa.orm.exc.MultipleResultsFound:
            return session.exec(select(cls), **spec).first()


class PeriodicTasksChanged(SQLModel, table=True):
    """Helper table for tracking updates to periodic tasks.

    This stores a single row with ``id=1``. ``last_update`` is updated via
    signals whenever anything changes in the :class:`~.PeriodicTask` model.
    Basically this acts like a DB data audit trigger.
    Doing this, so we also track deletions, and not just insert/update.
    """

    __tablename__ = "tasks_periodic_change"
    id: int = Field(
        default=None, primary_key=True, sa_column_kwargs={"autoincrement": False}
    )
    last_update: datetime = Field(
        sa_column=Column(sa.DateTime(timezone=True), nullable=False),
        default=nowfun(),
    )

    @classmethod
    def changed(cls, mapper, connection, target):
        """
        :param mapper: the Mapper which is the target of this event
        :param connection: the Connection being used
        :param target: the mapped instance being persisted
        """
        if not target.no_changes:
            cls.update_changed(mapper, connection, target)

    @classmethod
    def update_changed(
        cls, mapper, connection, target
    ):  # pylint: disable=unused-argument
        """
        :param mapper: the Mapper which is the target of this event
        :param connection: the Connection being used
        :param target: the mapped instance being persisted
        """
        logger.info("Database last time set to now")
        row = connection.execute(select(cls).where(cls.id == 1)).first()
        if row is None:
            connection.execute(sa.insert(cls).values(id=1, last_update=nowfun()))
        else:
            connection.execute(
                sa.update(cls).where(cls.id == 1).values(last_update=nowfun())
            )

    @classmethod
    def update_from_session(cls, session: Session, commit: bool = True):
        """
        :param session: the Session to use
        :param commit: commit the session if set to true
        """
        connection = session.connection()
        cls.update_changed(None, connection, None)
        if commit:
            connection.commit()

    @classmethod
    def last_change(cls, session: Session) -> Optional[datetime]:
        try:
            return session.get(cls, 1).last_update
        except sa.orm.exc.NoResultFound:
            pass


class ScheduledType(str, enum.Enum):
    """
    The type of a periodic task.
    """

    interval = "interval"
    crontab = "crontab"
    solar = "solar"
    clocked = "clocked"
    system = "system"


class PeriodicTask(ModelMixin, table=True):
    """Model representing a periodic task."""

    __tablename__ = "tasks_periodic_task"
    name: str = Field(max_length=200, unique=True)
    task: str = Field(max_length=200)
    types: Optional[ScheduledType] = Field(default=ScheduledType.interval)
    task_type: TaskType = Field(default=TaskType.playbook)
    interval_id: Optional[int] = Field(
        sa_type=BIGINT, default=None, foreign_key="tasks_interval_schedule.id"
    )
    interval: Optional[IntervalSchedule] = Relationship(
        back_populates="periodic_task",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    crontab_id: Optional[int] = Field(
        sa_type=BIGINT, default=None, foreign_key="tasks_crontab_schedule.id"
    )
    crontab: Optional[CrontabSchedule] = Relationship(
        back_populates="periodic_task",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    solar_id: Optional[int] = Field(
        sa_type=BIGINT, default=None, foreign_key="tasks_solar_schedule.id"
    )
    solar: Optional[SolarSchedule] = Relationship(
        back_populates="periodic_task",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    clocked_id: Optional[int] = Field(
        sa_type=BIGINT, default=None, foreign_key="tasks_clocked_schedule.id"
    )
    clocked: Optional[ClockedSchedule] = Relationship(
        back_populates="periodic_task",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    # These are JSON fields, so we can store any serializable data
    # For querying, we can use the JSON operators in SQLAlchemy
    # https://docs.sqlalchemy.org/en/14/dialects/postgresql.html#json-jsonb
    # Example:
    # .where(PeriodicTask.args.op("->>")(0).cast(Integer)== your_var)
    # This compares the first element of the args JSON array to your_var
    # It is important to set execution_options(synchronize_session="fetch")
    # This ensures the casts are done on the DB side, not the Python side
    args: list = Field(sa_column=Column(sa.JSON, nullable=False), default_factory=list)
    kwargs: dict = Field(
        sa_column=Column(sa.JSON, nullable=False), default_factory=dict
    )

    queue: Optional[str] = Field(max_length=200, nullable=True)

    # you can use low-level AMQP routing options here,
    # but you almost certaily want to leave these as None
    # http://docs.celeryproject.org/en/latest/userguide/routing.html#exchanges-queues-and-routing-keys
    exchange: Optional[str] = Field(max_length=200, nullable=True)
    routing_key: Optional[str] = Field(max_length=200, nullable=True)
    headers: Optional[dict] = Field(
        sa_column=Column(sa.JSON, nullable=False), default_factory=dict
    )
    priority: Optional[int] = Field(default=None, nullable=True)
    expires: Optional[datetime] = Field(
        sa_column=Column(sa.DateTime(timezone=True), nullable=True)
    )
    expire_seconds: Optional[int] = Field(default=None, nullable=True)
    one_off: bool = Field(default=False)
    start_time: Optional[datetime] = Field(
        sa_column=Column(sa.DateTime(timezone=True), nullable=True)
    )
    enabled: bool = Field(default=True)
    last_run_at: Optional[datetime] = Field(
        sa_column=Column(sa.DateTime(timezone=True), nullable=True)
    )
    total_run_count: int = Field(default=0, nullable=False)
    date_changed: datetime = Field(
        sa_column=Column(sa.DateTime(timezone=True), nullable=False),
        default=nowfun(),
    )
    description: str = Field(max_length=200, nullable=True)
    user_by: Optional[str] = Field(default=None, max_length=64, nullable=True)
    no_changes: bool = False

    @model_validator(mode="after")
    def validate_unique(self):
        selected_schedule_types = list(
            filter(
                lambda element: element is not None,
                [
                    self.interval,
                    self.crontab,
                    self.solar,
                    self.clocked,
                ],
            )
        )

        if len(selected_schedule_types) == 0:
            raise ValidationError.from_exception_data(
                title="Missing Schedule Type",
                line_errors=[
                    InitErrorDetails(
                        input=self.name,
                        type=PydanticCustomError(
                            "String",
                            "One of clocked, interval, crontab, or solar must be set.",
                        ),
                    )
                ],
            )

        err_msg = "Only one of clocked, interval, crontab, or solar must be set"
        if len(selected_schedule_types) > 1:
            error_info = {}
            for selected_schedule_type in selected_schedule_types:
                error_info[selected_schedule_type] = [err_msg]
            raise ValidationError.from_exception_data(
                title="Schedule Conflict",
                line_errors=[
                    InitErrorDetails(
                        input=self.name,
                        type=PydanticCustomError(
                            "String",
                            f"{error_info}",
                        ),
                    )
                ],
            )

        # clocked must be one off task
        if self.clocked and not self.one_off:
            err_msg = "clocked must be one off, one_off must set True"
            raise ValidationError.from_exception_data(
                title="Clocked Error",
                line_errors=[
                    InitErrorDetails(
                        input=self.name,
                        type=PydanticCustomError(
                            "String",
                            f"{err_msg}",
                        ),
                    )
                ],
            )
        if (self.expire_seconds is not None) and (self.expires is not None):
            raise ValidationError.from_exception_data(
                title="Expires Error",
                line_errors=[
                    InitErrorDetails(
                        input=self.name,
                        type=PydanticCustomError(
                            "String",
                            "Only one can be set, in expires and expire_seconds",
                        ),
                    )
                ],
            )
        return self

    @property
    def expires_(self):
        return self.expires or self.expire_seconds

    def __str__(self):
        fmt = "{0.name}: {{no schedule}}"
        if self.interval:
            fmt = "{0.name}: {0.interval}"
        if self.crontab:
            fmt = "{0.name}: {0.crontab}"
        if self.solar:
            fmt = "{0.name}: {0.solar}"
        if self.clocked:
            fmt = "{0.name}: {0.clocked}"
        return fmt.format(self)

    @property
    def scheduler(self):
        if self.interval_id:
            return self.interval
        if self.crontab_id:
            return self.crontab
        if self.solar_id:
            return self.solar
        if self.clocked_id:
            return self.clocked
        else:
            raise ValueError("No scheduler found")

    @property
    def schedule(self):
        return self.scheduler.schedule

    @computed_field
    @property
    def scheduled(
        self,
    ) -> Union[IntervalSchedule, CrontabSchedule, SolarSchedule, ClockedSchedule]:
        return self.scheduler

    @computed_field
    @property
    def schedule_str(self) -> str:
        if self.types == ScheduledType.interval or self.task == "tasks.ldap_sync":
            unit = "m"
            if self.interval.period == IntervalPeriod.HOURS:
                unit = "h"
            if self.interval.period == IntervalPeriod.DAYS:
                unit = "d"
            if self.interval.period == IntervalPeriod.SECONDS:
                unit = "s"
            return f"{self.interval.every}/{unit}"
        if self.types == ScheduledType.crontab or self.task in [
            "celery.backend_cleanup",
            "system.backend_cleanup",
        ]:
            return f"{self.crontab.minute} {self.crontab.hour} {self.crontab.day_of_week} {self.crontab.day_of_month} {self.crontab.month_of_year}"


listen(PeriodicTask, "after_insert", PeriodicTasksChanged.update_changed)
listen(PeriodicTask, "after_delete", PeriodicTasksChanged.update_changed)
listen(PeriodicTask, "after_update", PeriodicTasksChanged.update_changed)
listen(IntervalSchedule, "after_insert", PeriodicTasksChanged.update_changed)
listen(IntervalSchedule, "after_delete", PeriodicTasksChanged.update_changed)
listen(IntervalSchedule, "after_update", PeriodicTasksChanged.update_changed)
listen(CrontabSchedule, "after_insert", PeriodicTasksChanged.update_changed)
listen(CrontabSchedule, "after_delete", PeriodicTasksChanged.update_changed)
listen(CrontabSchedule, "after_update", PeriodicTasksChanged.update_changed)
listen(SolarSchedule, "after_insert", PeriodicTasksChanged.update_changed)
listen(SolarSchedule, "after_delete", PeriodicTasksChanged.update_changed)
listen(SolarSchedule, "after_update", PeriodicTasksChanged.update_changed)
