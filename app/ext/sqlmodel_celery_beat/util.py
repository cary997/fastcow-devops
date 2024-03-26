from datetime import datetime
from zoneinfo import ZoneInfo
from app.core.config import settings

NEVER_CHECK_TIMEOUT = 9999999999


def nowfun() -> datetime:
    return datetime.now(tz=ZoneInfo(settings.SYS_TIMEZONE))


def make_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=ZoneInfo(settings.SYS_TIMEZONE))
    else:
        return value.astimezone(ZoneInfo(settings.SYS_TIMEZONE))
