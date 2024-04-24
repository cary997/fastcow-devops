import os.path
from functools import lru_cache
from pathlib import Path

import yaml  # type: ignore
from pydantic import BaseModel, DirectoryPath, Field, HttpUrl, MySQLDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.utils.files_tools import mkdir_dir

BASE_DIR = Path(__file__).resolve().parent.parent

BASE_CONFIG_DIR = os.path.join(BASE_DIR.parent, "config")


def load(
    file=os.path.join(BASE_CONFIG_DIR, "config.yaml"),
    devfile=os.path.join(BASE_CONFIG_DIR, "config.dev.yaml"),
):
    """
    载入yaml文件
    """

    try:
        # 读取配置文件
        filepath = file
        # 本地开发时config.dev.yaml优先级最高覆盖config.yaml
        if os.path.exists(devfile):
            filepath = devfile
        yaml_file = open(filepath, encoding="utf-8")
        # 转换为dict格式
        config = yaml.load(yaml_file, Loader=yaml.FullLoader)
        return config
    except Exception as e:
        raise f"读取的文件不存在：{file} | {e}"


# 加载config.yaml配置
DefaultConfig = load()


class Settings(BaseSettings):
    """
    默认读取系统环境变量，若无对应key则使用config.yaml中配置
    """

    model_config = SettingsConfigDict(
        env_file=BASE_DIR.joinpath("config/.env"),
        case_sensitive=True,
        # env_prefix="my_prefix_"
    )

    # 项目基础路径
    BASE_DIR: DirectoryPath = BASE_DIR
    BASE_CONFIG_DIR: DirectoryPath = BASE_CONFIG_DIR
    BASE_TEMPLATES_DIR: DirectoryPath = BASE_DIR / "templates" / "build"
    # 数据存放路径
    DATA_PATH: DirectoryPath = Field(
        default=DefaultConfig["PATH"]["DATA_PATH"], validate_default=False
    )

    @computed_field
    @property
    def base_data_path(self) -> str:
        path = str(self.DATA_PATH)
        if path.endswith("/"):
            path = path[:-1]
        return path

    # 日志存放路径
    LOG_PATH: DirectoryPath = Field(
        default=DefaultConfig["PATH"]["LOG_PATH"], validate_default=False
    )

    @computed_field
    @property
    def base_logs_path(self) -> str:
        path = str(self.LOG_PATH)
        if path.endswith("/"):
            path = path[:-1]
        return path

    # FastAPI配置
    SYS_TITLE: str = DefaultConfig["SYSTEM"]["SYS_TITLE"]
    SYS_LINK: HttpUrl = DefaultConfig["SYSTEM"]["SYS_LINK"]
    SYS_DESCRIPTION: str = DefaultConfig["SYSTEM"]["SYS_DESCRIPTION"]
    SYS_VERSION: str = DefaultConfig["SYSTEM"]["SYS_VERSION"]
    SYS_ROUTER_PREFIX: str = DefaultConfig["SYSTEM"]["SYS_ROUTER_PREFIX"]
    SYS_ROUTER_AUTH2: str = DefaultConfig["SYSTEM"]["SYS_ROUTER_AUTH2"]
    SYS_ROUTER_REFRESH: str = DefaultConfig["SYSTEM"]["SYS_ROUTER_REFRESH"]
    SYS_ROUTER_SYNCROUTES: str = DefaultConfig["SYSTEM"]["SYS_ROUTER_SYNCROUTES"]
    SYS_OPENAPI_URL: str | None = DefaultConfig["SYSTEM"]["SYS_OPENAPI_URL"]
    SYS_TIMEZONE: str | None = DefaultConfig["SYSTEM"]["SYS_TIMEZONE"]

    # 跨域配置
    CORS_ORIGINS: list[str] = DefaultConfig["CORS"]["CORS_ORIGINS"]
    CORS_ALLOW_CREDENTIALS: bool = DefaultConfig["CORS"]["CORS_ALLOW_CREDENTIALS"]
    CORS_ALLOW_METHODS: list[str] = DefaultConfig["CORS"]["CORS_ALLOW_METHODS"]
    CORS_ALLOW_HEADERS: list[str] = DefaultConfig["CORS"]["CORS_ALLOW_HEADERS"]

    # 日志配置
    LOG_SERIALIZE: bool = DefaultConfig["LOG"]["LOG_SERIALIZE"]
    LOG_LEVER: str = DefaultConfig["LOG"]["LOG_LEVER"]
    LOG_ROTATION_TIME: str = DefaultConfig["LOG"]["LOG_ROTATION_TIME"]
    LOG_ROTATION_SIZE: str = DefaultConfig["LOG"]["LOG_ROTATION_SIZE"]
    LOG_RETENTION: str = DefaultConfig["LOG"]["LOG_RETENTION"]
    LOG_CONSOLE: bool = DefaultConfig["LOG"]["LOG_CONSOLE"]
    LOG_FILE: bool = DefaultConfig["LOG"]["LOG_FILE"]

    # 安全配置
    SECRET_KEY: str = DefaultConfig["SECURITY"]["SECRET_KEY"]
    SECRET_IV: str = DefaultConfig["SECURITY"]["SECRET_IV"]
    SECRET_JWT_KEY: str = DefaultConfig["SECURITY"]["SECRET_JWT_KEY"]
    SECRET_JWT_ALGORITHM: str = DefaultConfig["SECURITY"]["SECRET_JWT_ALGORITHM"]
    SECRET_JWT_EXP: int = DefaultConfig["SECURITY"]["SECRET_JWT_EXP"]
    SECRET_REJWT_EXP: int = DefaultConfig["SECURITY"]["SECRET_REJWT_EXP"]

    # 数据库配置
    DB_HOST: str = DefaultConfig["DATABASE"]["DB_HOST"]
    DB_PORT: int = DefaultConfig["DATABASE"]["DB_PORT"]
    DB_NAME: str = DefaultConfig["DATABASE"]["DB_NAME"]
    DB_USER: str = DefaultConfig["DATABASE"]["DB_USER"]
    DB_PASSWORD: str = DefaultConfig["DATABASE"]["DB_PASSWORD"]
    DB_QUERY: str = DefaultConfig["DATABASE"]["DB_QUERY"]
    DB_ECHO: bool = DefaultConfig["DATABASE"]["DB_ECHO"]

    def get_database_uri(self, scheme):
        return MySQLDsn.build(  # pylint: disable=no-member
            scheme=scheme,
            username=self.DB_USER,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=self.DB_PORT,
            path=self.DB_NAME,
            query=self.DB_QUERY,
        )

    @computed_field  # type: ignore[misc]
    @property
    def DATABASE_URI(self) -> MySQLDsn:
        """
        Mysql URI for database
        """
        return self.get_database_uri(scheme="mysql+mysqlconnector")

    @computed_field  # type: ignore[misc]
    @property
    def ASYNC_DATABASE_URI(self) -> MySQLDsn:
        """
        Mysql Async URI for database
        """
        return self.get_database_uri(scheme="mysql+asyncmy")

    # redis配置
    REDIS_MODE: str = DefaultConfig["CACHE"]["REDIS_MODE"]
    REDIS_DB: int = DefaultConfig["CACHE"]["REDIS_DB"]
    REDIS_ADDRESS: str = DefaultConfig["CACHE"]["REDIS_ADDRESS"]
    REDIS_USERNAME: str | None = DefaultConfig["CACHE"]["REDIS_USERNAME"]
    REDIS_PASSWORD: str | None = DefaultConfig["CACHE"]["REDIS_PASSWORD"]
    REDIS_SENTINEL_NAME: str | None = DefaultConfig["CACHE"]["REDIS_SENTINEL_NAME"]
    REDIS_ENCODING: str = DefaultConfig["CACHE"]["REDIS_ENCODING"]
    REDIS_MAX_CONNECTIONS: int = DefaultConfig["CACHE"]["REDIS_MAX_CONNECTIONS"]
    REDIS_SSL: bool = DefaultConfig["CACHE"]["REDIS_SSL"]
    REDIS_SSL_CERT_REQS: str | None = DefaultConfig["CACHE"]["REDIS_SSL_CERT_REQS"]
    REDIS_SSL_CA_CERTS: str | None = DefaultConfig["CACHE"]["REDIS_SSL_CA_CERTS"]

    # celery配置
    CELERY_BROKER_URL: str = DefaultConfig["CELERY"]["CELERY_BROKER_URL"]
    CELERY_RESULT_BACKEND: str = DefaultConfig["CELERY"]["CELERY_RESULT_BACKEND"]
    CELERY_RESULT_EXPIRES: int = DefaultConfig["CELERY"]["CELERY_RESULT_EXPIRES"]
    CELERY_CELERYD_PREFETCH_MULTIPLIER: int = DefaultConfig["CELERY"][
        "CELERY_CELERYD_PREFETCH_MULTIPLIER"
    ]
    CELERY_WORKER_MAX_TASKS_PER_CHILD: int = DefaultConfig["CELERY"][
        "CELERY_WORKER_MAX_TASKS_PER_CHILD"
    ]
    CELERY_WORKER_DISABLE_RATE_LIMITS: bool = DefaultConfig["CELERY"][
        "CELERY_WORKER_DISABLE_RATE_LIMITS"
    ]
    CELERY_ENABLE_UTC: bool = DefaultConfig["CELERY"]["CELERY_ENABLE_UTC"]


# 缓存配置信息
@lru_cache
def get_settings():
    return Settings()


# 配置文件实例化
settings = get_settings()


class BasePath(BaseModel):
    """
    项目路径
    """

    base_path: str = settings.base_data_path
    # 任务模版数据路径
    tasks_templates_path: str = f"{settings.base_data_path}/tasks/templates"
    # 任务执行元数据路径
    tasks_meta_path: str = f"{settings.base_data_path}/tasks/metadata"
    # 文件上传临时路径
    upload_temp_path: str = f"{settings.base_data_path}/tmp/upload"
    # 文件下载临时路径
    download_temp_path: str = f"{settings.base_data_path}/tmp/download"


@lru_cache
def get_base_path():
    return BasePath()


# 路径配置实例化
base_path = get_base_path()


def init_path() -> None:
    for k, v in base_path.model_dump().items():
        # 检查数据目录是否存在
        if not os.path.exists(v):
            mkdir_dir(v)


__all__ = [settings, base_path, init_path]
if __name__ == "__main__":
    init_path()
