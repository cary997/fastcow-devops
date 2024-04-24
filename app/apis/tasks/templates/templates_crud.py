import os
from typing import Any

from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import base_path
from app.models.tasks_model import TaskTemplates
from app.utils.files_tools import (
    create_file,
    mkdir_dir,
    move_dir_or_file,
    remove_dir,
    remove_file,
    rename_file_or_dir,
)

from . import templates_schema as schema


async def create_template(
    session: AsyncSession, template_create: schema.CreateTemplate
) -> TaskTemplates:
    db_template = TaskTemplates.model_validate(template_create)
    session.add(db_template)
    await session.commit()
    await session.refresh(db_template)
    mkdir_dir(f"{base_path.tasks_templates_path}/{str(db_template.id)}")
    return db_template


async def update_template_files(file_content: schema.UpdateTemplateFiles) -> Any:
    """
    更新任务模版文件
    """
    # 路径
    path_or_dest = os.path.join(base_path.tasks_templates_path, file_content.path)
    if file_content.action == "del":
        if file_content.type == 2:
            remove_dir(path_or_dest)
        if file_content.type == 3:
            remove_file(path_or_dest)
    if file_content.action == "rename":
        # 旧路径
        src = os.path.join(base_path.tasks_templates_path, file_content.old_path)
        rename_file_or_dir(src, path_or_dest)
    if file_content.action == "move":
        # 旧路径
        src = os.path.join(base_path.tasks_templates_path, file_content.old_path)
        move_dir_or_file(src, path_or_dest)
    if file_content.action == "add":
        if file_content.type == 2:
            mkdir_dir(path_or_dest)
        if file_content.type == 3:
            create_file(path_or_dest)
