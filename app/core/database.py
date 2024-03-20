from loguru import logger
from sqlmodel import Session, create_engine, select

from app.core.config import settings

engine = create_engine(str(settings.DATABASE_URI), echo=settings.DB_ECHO)


async def register_db() -> None:
    """
    启动时测试数据库连接
    """
    try:
        with Session(engine) as session:
            session.exec(select(1))
    except Exception as e:
        logger.error(e)
        raise e
