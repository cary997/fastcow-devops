import json

from app.core.cache import get_redis
from app.models.system_model import ldapConfig, ldapSync
from app.utils.format_tools import get_dict_target_value


def get_ldap_conn_conf() -> ldapConfig:
    redis = next(get_redis())
    data = redis.get("sys:settings")
    config = get_dict_target_value(json.loads(data), "ldap.config")
    return ldapConfig(**config)


def get_ldap_sync_conf() -> ldapSync:
    redis = next(get_redis())
    data = redis.get("sys:settings")
    config = get_dict_target_value(json.loads(data), "ldap.sync")
    return ldapSync(**config)


if __name__ == "__main__":
    a = get_ldap_conn_conf()
    print(a)
    attributes = a.attributes
    print(attributes)