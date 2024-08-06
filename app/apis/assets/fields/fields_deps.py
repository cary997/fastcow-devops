from loguru import logger
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.assets.assets_model import AssetsFields


async def get_or_create_fields(session: AsyncSession) -> AssetsFields:
    """
    获取或创建默认字段配置
    """
    fields_data = await session.get(AssetsFields, 1)
    if not fields_data:
        try:
            fields_data = AssetsFields.model_validate(AssetsFields(id=1))
            session.add(fields_data)
            await session.commit()
            await session.refresh(fields_data)
            return fields_data
        except Exception as e:  # pylint: disable=broad-exception-caught
            await session.rollback()
            logger.error(f"{e}")
    return fields_data


async def set_fields_depends(update_content: AssetsFields) -> dict:
    update_dict = update_content.model_dump(exclude_unset=True, exclude_none=True)
    return update_dict
