from enum import Enum
from typing import Optional

from pydantic import UUID4, computed_field
from sqlmodel import Field, SQLModel

from app.core.base import ModelBase, PagingQueryBaseModel, ResponseBase
from app.core.config import base_path
from app.models.tasks_model import TaskTemplates, TaskTemplatesBase, TaskType
from app.utils.files_tools import dir_to_tree


class CreateTemplate(TaskTemplatesBase):
    """
    创建任务模版
    """


class CreateTemplateResponse(ResponseBase):
    """
    创建任务模版响应
    """

    data: TaskTemplates = None


class UpdateTemplate(TaskTemplatesBase):
    """
    更新任务模版
    """

    name: str = Field(default=..., unique=True, description="模版名称")


class UpdateTemplateResponse(CreateTemplateResponse):
    """
    更新任务模版响应
    """


class TemplateQuery(SQLModel):
    """
    任务模版过滤不包含files字段
    """

    id: UUID4
    name: str = Field(default=..., unique=True, description="模版名称")
    task_type: TaskType = Field(default=TaskType.playbook, description="任务类型")
    desc: Optional[str] = Field(default=None, description="任务描述", nullable=True)


class GetTemplateResult(TemplateQuery, ModelBase):
    """
    查询任务模版结果
    """

    @computed_field
    @property
    def files(self) -> list[dict]:
        dir_tree = dir_to_tree(
            f"{base_path.tasks_templates_path}/{self.id}", root_name="workspace"
        )
        return [dir_tree]


class GetTemplateResponse(ResponseBase):
    """
    查询任务模版响应
    """

    data: Optional[GetTemplateResult] = None


class TemplateQueryResult(PagingQueryBaseModel):
    """
    任务模版过滤结果
    """

    result: Optional[list[TemplateQuery]] = None


class TemplateQueryResponse(ResponseBase):
    """
    任务模版过滤响应
    """

    data: Optional[TemplateQueryResult] = None


class DeleteTemplateResponse(ResponseBase):
    """
    删除任务模版响应
    """

    data: dict[str, str]


class UpdateFilesAction(str, Enum):
    """
    更新任务模版文件操作类型
    """

    create = "add"
    delete = "del"
    move = "move"
    rename = "rename"


class UpdateTemplateFiles(SQLModel):
    """
    更新任务模版文件
    """

    action: UpdateFilesAction = Field(default=None, description="操作类型")
    path: str = Field(default=None, description="路径")
    old_path: Optional[str] = Field(default=None, description="旧路径")
    type: int = Field(default=None, description="文件类型")
