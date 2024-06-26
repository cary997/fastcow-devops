import asyncio
import json
from builtins import anext
from typing import Any

from app.core.cache import get_async_redis
from app.utils.format_tools import get_dict_target_value


def is_json(data: str | None) -> bool:
    """
    判断是否为json
    """
    try:
        if data is None:
            return False
        json.loads(data)
    except ValueError:
        return False
    return True


async def redis_exists_key(key: str) -> bool:
    """
    key : reids中的key
    判断key是否存在，数据为空也视为不存在
    """
    _c = get_async_redis()
    cache = await anext(_c)
    # 返回值1和0
    state = await cache.exists(key)
    if not state:
        return False
    data = await cache.get(key)
    if not data:
        return False
    return True


async def get_redis_data(key: str, value_key: str | None = None) -> Any:
    """
    key : reids中的key
    value_key : 如果是个json可直接查找json里的字段
    """
    _c = get_async_redis()
    cache = await anext(_c)
    try:
        is_empty = await redis_exists_key(key)
        if not is_empty:
            return None
        data = await cache.get(key)
        if is_json(data):
            data = json.loads(data)
            if value_key:
                return get_dict_target_value(data, value_key)
        return data
    except Exception as e:
        raise e


async def set_redis_data(key: str, value: str | dict, **kwargs) -> None:
    """
    key : reids中的key
    value : 要存的数据
    """
    _c = get_async_redis()
    cache = await anext(_c)
    try:
        if isinstance(value, dict):
            value = json.dumps(value)
        await cache.set(key, value, **kwargs)
    except Exception as e:
        raise e


if __name__ == "__main__":
    asyncio.run(get_redis_data("sys:settings", "channels.email"))
    # asyncio.run(set_redis_data('k1', {'a': 1, 'b': 2}, ex=200))
    # asyncio.run(redis_exists_key('sys:settings'))
