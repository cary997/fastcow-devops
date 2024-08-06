from sqlmodel import SQLModel

from app.core.database import engine
from app.ext.sqlmodel_celery_beat.models import (
    ClockedSchedule,
    CrontabSchedule,
    IntervalSchedule,
    PeriodicTask,
    PeriodicTasksChanged,
    SolarSchedule,
)
from app.models.assets.assets_model import AssetsFields, AssetsGroups, AssetsHosts
from app.models.auth_model import Menus, Roles, RolesMenusLink, Users, UsersRolesLink
from app.models.system_model import SystemSettings
from app.models.tasks_model import TasksHistory, TaskTemplates

if __name__ == "__main__":

    def create_db_and_tables() -> None:
        """
        创建表
        """
        SQLModel.metadata.create_all(engine)

    create_db_and_tables()
