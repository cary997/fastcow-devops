from typing import Optional

from pydantic import BaseModel, Field

from app.core.base import PagingQueryBaseModel, ResponseBase
from app.models.tasks_model import TasksHistory


class TasksRunResponse(ResponseBase):
    """
    任务执行响应
    """

    data: Optional[TasksHistory] = None


class CheckConfigResult(BaseModel):
    """
    检查配置结果
    """

    rc: int = None
    status: str = None
    task_type: str = None
    stdout: Optional[str] = None


class CheckConfigResponse(ResponseBase):
    """
    检查配置响应
    """

    data: Optional[CheckConfigResult] = None


class DeleteListId(BaseModel):
    """
    删除任务历史参数
    """

    id_list: list[int]


class DeleteTasksHistoryResult(BaseModel):
    """
    删除任务历史响应
    """

    id: int
    task_id: str
    private_data_dir: str


class DeleteTasksHistoryResponse(ResponseBase):
    """
    删除任务历史响应
    """

    data: list[DeleteTasksHistoryResult]


class TasksHistoryQueryResult(PagingQueryBaseModel):
    """
    任务历史过滤结果
    """

    result: Optional[list[TasksHistory]] = None


class TasksHistoryQueryResponse(ResponseBase):
    """
    任务历史过滤响应
    """

    data: Optional[TasksHistoryQueryResult] = None


class GetHistoryResponse(ResponseBase):
    """
    查询任务历史响应
    """

    data: Optional[TasksHistory] = None


class GetTaskStdoutResponse(ResponseBase):
    """
    获取任务输出响应
    """

    data: Optional[bytes | str] = None


class HistoryStatisticsResult(BaseModel):
    """
    任务历史统计结果
    """

    exec_count: int = Field(0)
    exec_success_count: int = Field(0)
    exec_fail_count: int = Field(0)
    exec_running_count: int = Field(0)
    exec_duration_max: int = Field(0)
    exec_duration_min: int = Field(0)
    exec_duration_avg: int = Field(0)


class HistoryStatisticsResponse(ResponseBase):
    """
    任务历史统计响应
    """

    data: Optional[HistoryStatisticsResult] = None
