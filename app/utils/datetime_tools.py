from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.config import settings


def utc_to_local(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=ZoneInfo('UTC'))
    value = value.astimezone(ZoneInfo(settings.SYS_TIMEZONE)).replace(tzinfo=None)
    return value
