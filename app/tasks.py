from celery import Celery
from kombu import Exchange, Queue

from app.core.config import settings
from app.ext.sqlmodel_celery_beat.schedulers import DatabaseScheduler

ds = DatabaseScheduler
beat_scheduler = "app.ext.sqlmodel_celery_beat.schedulers:DatabaseScheduler"
result_backend = (
    f"db+{str(settings.DATABASE_URI)}"
    if settings.CELERY_RESULT_BACKEND == "DATABASE"
    else settings.CELERY_RESULT_BACKEND
)
# 默认的路由，实际投递任务时可以手动指定队列

# https://docs.celeryq.dev/en/stable/userguide/configuration.html#std-setting-worker_concurrency
config = {
    "broker_url": settings.CELERY_BROKER_URL,
    "result_backend": result_backend,
    "celeryd_prefetch_multiplier": settings.CELERY_CELERYD_PREFETCH_MULTIPLIER,
    "worker_max_tasks_per_child": settings.CELERY_WORKER_MAX_TASKS_PER_CHILD,
    "worker_disable_rate_limits": settings.CELERY_WORKER_DISABLE_RATE_LIMITS,
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
    "task_default_queue": "default",
    "task_default_exchange_type": "direct",
    "task_default_routing_key": "default",
    "task_queues": [
        Queue("default", Exchange("default", type="direct"), routing_key="default"),
        Queue(
            "asb_temp_task",
            Exchange("ansible", type="direct"),
            routing_key="ansible.temp",
        ),
        Queue(
            "asb_scheduled_task",
            Exchange("ansible", type="direct"),
            routing_key="ansible.scheduled",
        ),
    ],
    "task_default_priority": 5,
    "task_queue_max_priority": 10,
    "task_routes": {
        "tasks.asb_temp_task": {
            "queue": "asb_temp_task",
            "exchange": "ansible",
            "exchange_type": "direct",
            "routing_key": "ansible.temp",
        },
        "tasks.asb_scheduled_task": {
            "queue": "asb_scheduled_task",
            "exchange": "ansible",
            "exchange_type": "direct",
            "routing_key": "ansible.scheduled",
        },
    },
}

celery = Celery(__name__)

celery.config_from_object(config)

celery.autodiscover_tasks(
    [
        "app.ext.ansible_tsk",
        "app.ext.ldap_tsk",
        "app.ext.channels_tsk",
        "app.ext.cleanup_tsk",
    ]
)

# celery -A app.tasks:celery worker -l info -P eventlet
# celery -A app.tasks:celery beat -S app.tasks:ds -l info
