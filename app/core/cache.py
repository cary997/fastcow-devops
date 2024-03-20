from typing import Any, AsyncGenerator, Union

from fastapi import FastAPI
from redis import asyncio as aioredis

from app.core.config import settings


class RedisMixin:
    """
    Redis 连接
    """
    mode = settings.REDIS_MODE
    host = settings.REDIS_ADDRESS
    db = settings.REDIS_DB
    username = settings.REDIS_USERNAME
    password = settings.REDIS_PASSWORD
    sentinel_name = settings.REDIS_SENTINEL_NAME
    encoding = settings.REDIS_ENCODING
    decode_responses = True
    max_connections = settings.REDIS_MAX_CONNECTIONS
    ssl = settings.REDIS_SSL
    ssl_cert_reqs = settings.REDIS_SSL_CERT_REQS
    ssl_ca_certs = settings.REDIS_SSL_CA_CERTS

    @property
    async def redis_standalone_conn(self) -> aioredis.Redis:
        """
        单机
        :return:
        """
        return aioredis.Redis(
            host=self.host.split(":")[0],
            port=int(self.host.split(":")[-1]),
            username=self.username,
            password=self.password,
            db=self.db,
            decode_responses=self.decode_responses,
            max_connections=self.max_connections,
            ssl=self.ssl,
            ssl_cert_reqs=self.ssl_cert_reqs,
            ssl_ca_certs=self.ssl_ca_certs,
        )

    @property
    async def redis_sentinel_conn(self) -> aioredis.Sentinel:
        """
        哨兵
        :return:
        """
        sentinel_list = []
        for address in self.host.split(","):
            sentinel_host = address.split(":")[0]
            sentinel_port = address.split(":")[-1]
            sentinel_list.append((sentinel_host, sentinel_port))
        return aioredis.Sentinel(
            sentinels=sentinel_list,
            username=self.username,
            password=self.password,
            db=self.db,
            decode_responses=self.decode_responses,
            max_connections=self.max_connections,
            ssl=self.ssl,
            ssl_cert_reqs=self.ssl_cert_reqs,
            ssl_ca_certs=self.ssl_ca_certs,
        )

    @property
    async def redis_cluster_conn(self) -> aioredis.RedisCluster:
        """
        集群
        :return:
        """
        startup_nodes = []
        for address in self.host.split(","):
            startup_nodes.append(
                aioredis.cluster.ClusterNode(
                    address.split(":")[0], address.split(":")[-1]
                )
            )
        return aioredis.RedisCluster(
            startup_nodes=startup_nodes,
            username=self.username,
            password=self.password,
            decode_responses=self.decode_responses,
            ssl=self.ssl,
            ssl_cert_reqs=self.ssl_cert_reqs,
            ssl_ca_certs=self.ssl_ca_certs,
        )

    @property
    async def connect_redis(self):
        """
        连接redis
        """

        if self.mode == "standalone":
            redis_conn = await self.redis_standalone_conn
        elif self.mode == "sentinel":
            redis_conn = await self.redis_sentinel_conn
        elif self.mode == "cluster":
            redis_conn = await self.redis_cluster_conn
        else:
            raise ValueError("Redis mode not supported")
        try:
            await redis_conn.ping()
        except aioredis.ConnectionError as e:
            raise f"Redis连接失败 - {e}"
        return redis_conn


async def register_redis(app: FastAPI) -> None:
    """
    注册redis测试连接
    """
    app.state.cache = await RedisMixin().connect_redis


redisCache = Union[aioredis.Redis, aioredis.Sentinel, aioredis.RedisCluster]


async def get_redis() -> AsyncGenerator[redisCache, Any]:
    """
    获取redis连接
    """
    _redis_coon = await RedisMixin().connect_redis
    try:
        yield _redis_coon
    finally:
        await _redis_coon.close()


if __name__ == "__main__":
    import asyncio

    a = asyncio.run(RedisMixin().connect_redis)
    print(type(a))
    print(a)
