from collections.abc import AsyncGenerator, Generator

from fastapi import FastAPI
from redis import Redis, RedisCluster, Sentinel
from redis import asyncio as aioredis
from redis.asyncio.cluster import ClusterNode as AioClusterNode
from redis.cluster import ClusterNode

from app.core.config import settings


class RedisConfig:
    """
    Redis 连接参数
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

    def get_sentinel_list(self) -> list[str]:
        """
        哨兵URI格式化
        """
        sentinel_list = []
        for address in self.host.split(","):
            sentinel_host = address.split(":")[0]
            sentinel_port = address.split(":")[-1]
            sentinel_list.append((sentinel_host, sentinel_port))
        return sentinel_list

    def get_cluster_startup_nodes(self, mode: bool = True) -> list[str]:
        """
        集群URI格式化
        mode true sync false Async
        """
        startup_nodes = []
        for address in self.host.split(","):
            node = address.split(":")[0]
            node_port = address.split(":")[-1]
            startup_nodes.append(
                ClusterNode(node, node_port)
                if mode
                else AioClusterNode(node, node_port)
            )
        return startup_nodes


class RedisMixin(RedisConfig):
    """
    Redis 连接
    """

    @property
    def redis_standalone_conn(self) -> Redis:
        """
        单机
        :return:
        """
        return Redis(
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
    def redis_sentinel_conn(self) -> Sentinel:
        """
        哨兵
        :return:
        """
        return Sentinel(
            sentinels=self.get_sentinel_list(),
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
    def redis_cluster_conn(self) -> aioredis.RedisCluster:
        """
        集群
        :return:
        """

        return RedisCluster(
            startup_nodes=self.get_cluster_startup_nodes(),
            username=self.username,
            password=self.password,
            decode_responses=self.decode_responses,
            ssl=self.ssl,
            ssl_cert_reqs=self.ssl_cert_reqs,
            ssl_ca_certs=self.ssl_ca_certs,
        )

    @property
    def connect_redis(self):
        """
        连接redis
        """

        if self.mode == "standalone":
            redis_conn = self.redis_standalone_conn
        elif self.mode == "sentinel":
            redis_conn = self.redis_sentinel_conn
        elif self.mode == "cluster":
            redis_conn = self.redis_cluster_conn
        else:
            raise ValueError("Redis mode not supported")
        try:
            redis_conn.ping()
        except ConnectionError as e:
            raise f"Redis连接失败 - {e}"
        return redis_conn


class AsyncRedisMixin(RedisConfig):
    """
    AsyncRedis 连接
    """

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
        return aioredis.Sentinel(
            sentinels=self.get_sentinel_list(),
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
        return aioredis.RedisCluster(
            startup_nodes=self.get_cluster_startup_nodes(mode=False),
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
    app.state.cache = await AsyncRedisMixin().connect_redis


def get_redis() -> Generator[Redis, None, None]:
    """
    获取Redis连接
    """
    redis_coon = RedisMixin().connect_redis
    try:
        yield redis_coon
    finally:
        redis_coon.close()


async def get_async_redis() -> AsyncGenerator[aioredis.Redis, None, None]:
    """
    获取aioRedis连接
    """
    _redis_coon = await AsyncRedisMixin().connect_redis
    try:
        yield _redis_coon
    finally:
        await _redis_coon.close()


if __name__ == "__main__":
    import asyncio

    a = asyncio.run(AsyncRedisMixin().connect_redis)
    print(type(a))
    print(a)
