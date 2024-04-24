"""Beat Scheduler Implementation."""

import datetime
import math
from multiprocessing.util import Finalize

import sqlalchemy as sa
from celery import Celery, current_app, schedules
from celery.beat import ScheduleEntry, Scheduler
from celery.utils.log import get_logger
from celery.utils.time import maybe_make_aware
from kombu.utils.encoding import safe_repr, safe_str
from kombu.utils.json import loads
from sqlmodel import Session, create_engine, select

from .clockedschedule import clocked
from .models import (
    ClockedSchedule,
    CrontabSchedule,
    IntervalSchedule,
    PeriodicTask,
    PeriodicTasksChanged,
    SolarSchedule,
)
from .util import NEVER_CHECK_TIMEOUT, nowfun

logger = get_logger("sqlmodel_celery_beat.schedulers")
# This scheduler must wake up more frequently than the
# regular of 5 minutes because it needs to take external
# changes to the schedule into account.
DEFAULT_MAX_INTERVAL = 5  # seconds

ADD_ENTRY_ERROR = """\
Cannot add entry %r to database schedule: %r. Contents: %r
"""


class ModelEntry(ScheduleEntry):
    """Scheduler entry taken from database row."""

    model_schedules = (
        (schedules.crontab, CrontabSchedule, "crontab"),
        (schedules.schedule, IntervalSchedule, "interval"),
        (schedules.solar, SolarSchedule, "solar"),
        (clocked, ClockedSchedule, "clocked"),
    )
    save_fields = ["last_run_at", "total_run_count", "no_changes"]

    def __init__(
        self, model: PeriodicTask, app=None, session_func=None
    ):  # pylint: disable=super-init-not-called
        """Initialize the model entry."""
        self.app = app or current_app._get_current_object()
        self.name = model.name
        self.task = model.task
        try:
            self.schedule = model.schedule
            logger.debug("schedule: {}".format(self.schedule))
        except Exception:
            logger.error(
                "Disabling schedule %s that was removed from database",
                self.name,
            )
            self._disable(model)
        try:
            self.args = model.args
            self.kwargs = model.kwargs
        except ValueError as exc:
            logger.exception(
                "Removing schedule %s for argument deseralization error: %r",
                self.name,
                exc,
            )
            self._disable(model)

        self.options = {}
        for option in ["queue", "exchange", "routing_key", "priority"]:
            value = getattr(model, option)
            if value is None:
                continue
            self.options[option] = value

        if getattr(model, "expires_", None):
            self.options["expires"] = getattr(model, "expires_")

        self.options["headers"] = loads(model.headers or "{}")
        self.options["periodic_task_name"] = model.name

        self.total_run_count = model.total_run_count
        self.model = model

        if not model.last_run_at:
            model.last_run_at = self._default_now()
            # if last_run_at is not set and
            # model.start_time last_run_at should be in way past.
            # This will trigger the job to run at start_time
            # and avoid the heap block.
            if self.model.start_time:
                model.last_run_at = model.last_run_at - datetime.timedelta(
                    days=365 * 30
                )

        self.last_run_at = model.last_run_at
        self.session_func = session_func

    def _disable(self, model: PeriodicTask):
        with self.session_func() as session:
            model.enabled = False
            model.no_changes = False
            model.save(session=session)

    def is_due(self) -> schedules.schedstate:
        if not self.model.enabled:
            # 5 second delay for re-enable.
            return schedules.schedstate(False, 5.0)

        # START DATE: only run after the `start_time`, if one exists.
        if self.model.start_time is not None:
            now = self._default_now()
            if getattr(self.app.conf, "CELERY_BEAT_TZ_AWARE", True):
                now = maybe_make_aware(self._default_now())

            if now < self.model.start_time:
                # The datetime is before the start date - don't run.
                # send a delay to retry on start_time
                delay = math.ceil((self.model.start_time - now).total_seconds())
                return schedules.schedstate(False, delay)

        # ONE OFF TASK: Disable one off tasks after they've ran once
        if self.model.one_off and self.model.enabled and self.model.total_run_count > 0:
            with self.session_func() as session:
                self.model.enabled = False
                self.model.total_run_count = 0  # Reset
                self.model.no_changes = False  # Mark the model entry as changed
                self.model.save(session=session)
                # Don't recheck
                return schedules.schedstate(False, NEVER_CHECK_TIMEOUT)

        # CAUTION: make_aware assumes settings.TIME_ZONE for naive datetimes,
        # while maybe_make_aware assumes utc for naive datetimes
        # tz = self.app.timezone
        # last_run_at_in_tz = maybe_make_aware(self.last_run_at).astimezone(tz)
        # return self.schedule.is_due(last_run_at_in_tz)
        tz = self.app.timezone
        return self.schedule.is_due(self.last_run_at.replace(tzinfo=tz))

    def _default_now(self):
        if getattr(self.app.conf, "CELERY_BEAT_TZ_AWARE", True):
            now = datetime.datetime.now(self.app.timezone)
        else:
            # this ends up getting passed to maybe_make_aware, which expects
            # all naive datetime objects to be in utc time.
            now = nowfun()
        return now

    def __next__(self):
        self.model.last_run_at = self._default_now()
        self.model.total_run_count += 1
        self.model.no_changes = True
        return self.__class__(self.model, session_func=self.session_func)

    next = __next__  # for 2to3

    def save(self):
        """Save the model entry to the database."""
        with self.session_func() as session:
            session.add(self.model)
            session.commit()

    @classmethod
    def to_model_schedule(cls, schedule: schedules.schedule, session: Session):
        for schedule_type, model_type, model_field in cls.model_schedules:
            schedule = schedules.maybe_schedule(schedule)
            if isinstance(schedule, schedule_type):
                model_schedule = model_type.from_schedule(schedule)
                model_schedule.save(session)
                return model_schedule, model_field
        raise ValueError(f"Cannot convert schedule type {schedule!r} to model")

    @classmethod
    def from_entry(
        cls,
        name: str,
        session: Session,
        app: Celery | None = None,
        **entry,
    ):
        task = PeriodicTask(
            name=name,
            **entry,
        )
        session.add(task)
        session.commit()
        return cls(task, app=app)

    def __repr__(self):
        return "<ModelEntry: {} {}(*{}, **{}) {}>".format(  # pylint: disable=consider-using-f-string
            safe_str(self.name),
            self.task,
            safe_repr(self.args),
            safe_repr(self.kwargs),
            self.schedule,
        )


class DatabaseScheduler(Scheduler):
    """Database-backed Beat Scheduler."""

    _schedule = None
    _last_timestamp = None
    _initial_read = True
    _heap_invalidated = False

    def __init__(
        self, dburi: str | None = None, *args, **kwargs
    ):  # pylint: disable=keyword-arg-before-vararg
        """Initialize the database scheduler."""
        self._dirty = set()
        # DB handling
        self.app = kwargs.get("app") or current_app._get_current_object()
        self.dburi = dburi or self.app.conf.beat_dburi
        self.engine = create_engine(self.dburi)
        Scheduler.__init__(self, *args, **kwargs)
        self._finalize = Finalize(self, self.sync, exitpriority=5)
        self.max_interval = (
            kwargs.get("max_interval")
            or self.app.conf.beat_max_loop_interval
            or DEFAULT_MAX_INTERVAL
        )

    def get_session(self) -> Session:
        return Session(self.engine, expire_on_commit=False)

    def _get_session_func(self):
        return self.get_session

    def setup_schedule(self):
        logger.info("setup_schedule")
        self.install_default_entries(self.schedule)
        self.update_from_dict(self.app.conf.beat_schedule)

    def all_as_schedule(self) -> dict[str, ModelEntry]:
        logger.debug("DatabaseScheduler: Fetching database schedule")
        s = {}
        with self.get_session() as session:
            for model in session.exec(
                select(PeriodicTask).where(PeriodicTask.enabled)
            ).all():
                try:
                    s[model.name] = ModelEntry(
                        model, app=self.app, session_func=self._get_session_func()
                    )
                except ValueError:
                    pass
        return s

    def schedule_changed(self):
        with self.get_session() as session:
            changes = session.get(PeriodicTasksChanged, 1)
            if not changes:
                session.add(PeriodicTasksChanged(id=1))
                session.commit()
                return False
            last, ts = self._last_timestamp, changes.last_update
            if ts and ts > (last if last else ts):
                self._last_timestamp = ts
                return True
        self._last_timestamp = ts
        return False

    def reserve(self, entry):
        new_entry = next(entry)
        # Need to store entry by name, because the entry may change
        # in the mean time.
        self._dirty.add(new_entry.name)
        return new_entry

    def sync(self):
        _tried = set()
        _failed = set()
        try:
            while self._dirty:
                name = self._dirty.pop()
                try:
                    self._schedule[name].save()
                    logger.debug("{name} save to database".format(name=name))
                    _tried.add(name)
                except (KeyError, TypeError, sa.exc.OperationalError):
                    _failed.add(name)
        except sa.exc.DatabaseError as exc:
            logger.exception("Database error while sync: %r", exc)
        except sa.exc.InterfaceError as exc:
            logger.warning(
                "DatabaseScheduler: InterfaceError in sync(), "
                "waiting to retry in next call..."
            )
        finally:
            # retry later, only for the failed ones
            self._dirty |= _failed

    def update_from_dict(
        self, mapping: dict[str, dict]
    ):  # pylint: disable=arguments-renamed
        s = {}
        for name, entry_fields in mapping.items():
            try:
                entry = ModelEntry.from_entry(
                    name, session=self.get_session(), app=self.app, **entry_fields
                )
                if entry.model.enabled:
                    s[name] = entry

            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.exception(ADD_ENTRY_ERROR, name, exc, entry_fields)
        self.schedule.update(s)

    def install_default_entries(self, data):
        entries = {}
        if self.app.conf.result_expires:
            # Check if celery.backend_cleanup is not already in the schedule,
            if (
                not self.get_session()
                .exec(
                    select(PeriodicTask).where(
                        PeriodicTask.name == "celery.backend_cleanup"
                    )
                )
                .first()
            ):
                entries.setdefault(
                    "celery.backend_cleanup",
                    {
                        "task": "celery.backend_cleanup",
                        "types": "system",
                        "task_type": "SysApi",
                        "user_by": "admin",
                        "priority": 9,
                        "expire_seconds": 12 * 3600,
                        "crontab": CrontabSchedule(minute="0", hour="4"),
                    },
                )
            if (
                not self.get_session()
                .exec(
                    select(PeriodicTask).where(
                        PeriodicTask.name == "system.backend_cleanup"
                    )
                )
                .first()
            ):
                entries.setdefault(
                    "system.backend_cleanup",
                    {
                        "task": "system.backend_cleanup",
                        "types": "system",
                        "task_type": "SysApi",
                        "user_by": "admin",
                        "priority": 9,
                        "expire_seconds": 12 * 3600,
                        "kwargs": {
                            "task_history_expire": 7,
                        },
                        "crontab": CrontabSchedule(minute="0", hour="3"),
                    },
                )
        self.update_from_dict(entries)

    def schedules_equal(self, *args, **kwargs):
        if self._heap_invalidated:
            self._heap_invalidated = False
            return False
        return super().schedules_equal(*args, **kwargs)

    @property
    def schedule(self):
        initial = update = False
        if self._initial_read:
            logger.debug("DatabaseScheduler: initial read")
            initial = update = True
            self._initial_read = False
        elif self.schedule_changed():
            logger.info("DatabaseScheduler: Schedule changed.")
            update = True

        if update:
            self.sync()
            self._schedule = self.all_as_schedule()
            # the schedule changed, invalidate the heap in Scheduler.tick
            if not initial:
                self._heap = []
                self._heap_invalidated = True
        return self._schedule

    @property
    def info(self):
        """override"""
        # return infomation about Schedule
        return f"    . db -> {self.dburi}"
