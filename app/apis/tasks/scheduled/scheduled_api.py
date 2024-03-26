from typing import Any

from fastapi import APIRouter

from app.depends import AsyncSessionDep
from app.ext.sqlmodel_celery_beat.models import PeriodicTask

router = APIRouter()


@router.post('/add')
async def add_scheduled(
        session: AsyncSessionDep, create_tasks: PeriodicTask
) -> Any:
    return {}