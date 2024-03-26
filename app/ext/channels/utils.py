import json

from app.core.cache import get_redis
from app.models.system_model import mailServerSettings
from app.utils.format_tools import get_dict_target_value


def get_mail_conf() -> mailServerSettings:
    redis = next(get_redis())
    data = redis.get("sys:settings")
    config = get_dict_target_value(json.loads(data), "channels.email")
    return mailServerSettings(**config)