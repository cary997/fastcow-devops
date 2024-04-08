from sqlmodel import SQLModel

from app.core.database import engine
from app.models.tasks_model import TaskTemplates

if __name__ == "__main__":

    def create_db_and_tables() -> None:
        """
        创建表
        """
        SQLModel.metadata.create_all(engine)

    create_db_and_tables()
