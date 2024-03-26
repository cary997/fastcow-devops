from loguru import logger
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import Session, create_engine, select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.config import settings

engine = create_engine(str(settings.DATABASE_URI), echo=settings.DB_ECHO)
async_engine = create_async_engine(
    str(settings.ASYNC_DATABASE_URI), echo=settings.DB_ECHO
)


async def register_db() -> None:
    """
    启动时测试数据库连接
    """
    try:
        with Session(engine) as sync_session:
            sync_session.exec(select(1))
        async with AsyncSession(async_engine) as async_session:
            await async_session.exec(select(1))
    except Exception as e:
        logger.error(e)
        raise e
