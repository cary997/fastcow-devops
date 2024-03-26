from celery import Celery

from app.core.config import settings
from app.ext.sqlmodel_celery_beat.schedulers import (  # pylint: disable=unused-import
    DatabaseScheduler,
)

beat_scheduler = "app.ext.sqlmodel_celery_beat.schedulers:DatabaseScheduler"
result_backend = (
    f"db+{str(settings.DATABASE_URI)}"
    if settings.CELERY_RESULT_BACKEND == "DATABASE"
    else settings.CELERY_RESULT_BACKEND
)

# https://docs.celeryq.dev/en/stable/userguide/configuration.html#std-setting-worker_concurrency
config = {
    "broker_url": settings.CELERY_BROKER_URL,
    "result_backend": result_backend,
    "celeryd_prefetch_multiplier": settings.CELERY_CELERYD_PREFETCH_MULTIPLIER,
    "worker_max_tasks_per_child": settings.CELERY_WORKER_MAX_TASKS_PER_CHILD,
    "celery_disable_rate_limits": settings.CELERY_WORKER_DISABLE_RATE_LIMITS,
    "enable_utc": settings.CELERY_ENABLE_UTC,
    "timezone": settings.SYS_TIMEZONE,
    "beat_dburi": str(settings.DATABASE_URI),
    "result_extended": True,
    "result_expires": settings.CELERY_RESULT_EXPIRES,
    # Celery 6.0 Not sure whether to use
    "broker_connection_retry_on_startup": False,
    "database_table_names": {
        "task": "tasks_meta",
        "group": "tasks_group_meta",
    },
}

celery = Celery(__name__)

celery.config_from_object(config)

celery.autodiscover_tasks(["app.ext.ldap", "app.ext.channels"])

# celery -A app.tasks:celery worker -l info -P eventlet
# celery -A app.tasks:celery beat -S app.tasks:DatabaseScheduler -l info

@celery.task(name='tasks.add')
def add(x, y):
    return x + y