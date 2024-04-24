import time

from loguru import logger
from sqlmodel import select

from app.core.config import base_path
from app.depends import get_session
from app.models.tasks_model import TasksHistory
from app.tasks import celery
from app.utils.files_tools import mkdir_dir, remove_dir


@celery.task(bind=True, name="system.backend_cleanup")
def system_backend_cleanup(self, **kwargs):
    """
    系统清理任务
    任务历史、临时目录清理
    """
    expire = kwargs.get("task_history_expire")
    if not expire:
        expire = 60 * 60 * 24 * 7
    else:
        expire = 60 * 60 * 24 * expire
    time_now = int(time.time())
    expire_time = time_now - expire
    session = next(get_session())
    expire_time_history = session.exec(
        select(TasksHistory).where(TasksHistory.task_start_time <= expire_time)
    ).all()
    private_data_dir_list = []
    for history in expire_time_history:
        private_data_dir: str = history.task_kwargs.get("private_data_dir")
        if private_data_dir:
            private_data_dir_list.append({history.task_name: private_data_dir})
            remove_dir(private_data_dir)
        session.delete(history)
    session.commit()
    logger.info(f"清理历史任务成功，删除{len(private_data_dir_list)}条数据")
    remove_dir(base_path.upload_temp_path)
    mkdir_dir(base_path.upload_temp_path)
    logger.info(f"清理临时上传目录成功，删除{base_path.upload_temp_path}")
    remove_dir(base_path.download_temp_path)
    mkdir_dir(base_path.download_temp_path)
    logger.info(f"清理临时下载目录成功，删除{base_path.download_temp_path}")
    return {"result": private_data_dir_list}
