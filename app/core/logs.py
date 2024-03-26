import logging
import os
import sys
from datetime import datetime, timedelta
from pprint import pformat

from loguru import _string_parsers as string_parser
from loguru import logger

from app.core.config import settings


class InterceptHandler(logging.Handler):
    """
    Default handler from examples in loguru documentaion.
    See https://loguru.readthedocs.io/en/stable/overview.html#entirely-compatible-with-standard-logging
    """

    def emit(self, record: logging.LogRecord):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno  # type: ignore

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back  # type: ignore
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def format_record(record: dict) -> str:
    """
    Custom format for loguru loggers.
    Uses pformat for log any data like request/response body during debug.
    Works with logging if loguru handler it.
    Example:
    # >>> payload = [{"users":[{"name": "Nick", "age": 87, "is_active": True}, {"name": "Alex", "age": 27, "is_active": True}], "count": 2}]
    # >>> logger.bind(payload=).debug("users payload")
    # >>> [   {   'count': 2,
    # >>>         'users': [   {'age': 87, 'is_active': True, 'name': 'Nick'},
    # >>>                      {'age': 27, 'is_active': True, 'name': 'Alex'}]}]
    """

    format_string = (
        "<green>{time:YYYY-MM-DD HH:mm:ss:SSS}</green> | <level>{level.name}</level> | <cyan>{"
        "name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <cyan>{process}</cyan>:<cyan>{"
        "thread}</cyan> | <level>{message}</level> "
    )
    if record["extra"].get("payload") is not None:
        record["extra"]["payload"] = pformat(
            record["extra"]["payload"], indent=4, compact=True, width=88
        )
        format_string += "\n<level>{extra[payload]}</level>"

    format_string += "{exception}\n"
    return format_string


class Rotator:
    """
    Rotates log files based on size and time.
    """

    def __init__(self, str_size, str_time):
        self._size = string_parser.parse_size(str_size)
        at = string_parser.parse_time(str_time)
        now = datetime.now()
        today_at_time = now.replace(hour=at.hour, minute=at.minute, second=at.second)
        if now >= today_at_time:
            # the current time is already past the target time so it would rotate already
            # add one day to prevent an immediate rotation
            self._next_rotate = today_at_time + timedelta(days=1)
        else:
            self._next_rotate = today_at_time

    def should_rotate(self, message, file) -> bool:
        file.seek(0, 2)
        if file.tell() + len(message) > self._size:
            return True
        if message.record["time"].timestamp() > self._next_rotate.timestamp():
            self._next_rotate += timedelta(days=1)
            return True
        return False


def init_logs() -> None:
    LOG_LEVER = settings.LOG_LEVER
    # 这里的操作是为了改变默认的logger，使之采用loguru的logger
    # change handler for default uvicorn\sqlalchemy\fastapi logger
    intercept_handler = InterceptHandler()

    loggers = (
        logging.getLogger(name)
        for name in logging.root.manager.loggerDict  # pylint: disable=no-member
        if name.startswith("uvicorn") or name.startswith("fastapi")
        # or name.startswith("sqlalchemy")
    )
    for _logger in loggers:
        _logger.handlers = [intercept_handler]
        _logger.setLevel(LOG_LEVER)
        _logger.propagate = False
    # 先清空默认包含stderr
    logger.remove()

    # 判断是否输出控制台
    if settings.LOG_CONSOLE:
        logger.add(
            sink=sys.stderr,
            level=LOG_LEVER,
            format=format_record,  # type: ignore
            serialize=settings.LOG_SERIALIZE,
        )

    # 判断是否输出到文件
    if settings.LOG_FILE:
        # 初始化日志切割函数
        rotator = Rotator(settings.LOG_ROTATION_SIZE, settings.LOG_ROTATION_TIME)
        # 公共参数
        base_config = {
            "level": LOG_LEVER,
            "format": format_record,
            "rotation": rotator.should_rotate,
            "retention": settings.LOG_RETENTION,
            "enqueue": True,
            "diagnose": True,
            "backtrace": True,
            "serialize": settings.LOG_SERIALIZE,
        }
        # 日志文件路径
        access_log = os.path.join(settings.LOG_PATH, "access.log")
        error_log = os.path.join(settings.LOG_PATH, "error.log")
        # 添加记录器
        logger.add(
            sink=access_log,
            filter=lambda record: record["level"].no <= 30,
            **base_config,
        )
        logger.add(
            sink=error_log,
            filter=lambda record: record["level"].no > 30,
            **base_config,
        )
        logger.info(f"Access Log File Path - {access_log}")
        logger.info(f"Error Log File Path - {error_log}")

    logger.success("Logger initialization")


if __name__ == "__main__":
    init_logs()

    logger.trace("trace")
    logger.debug("debug")
    logger.info("info")
    logger.success("success")
    logger.warning("warnig")
    logger.error("error")
    logger.critical("critical")
    logger.bind(payload={"name": "test"}).info("test message")
