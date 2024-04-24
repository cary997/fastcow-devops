import json
import os
import os.path
import time
from typing import Any, Optional

import ansible_runner
from ansible_runner import Runner, RunnerConfig
from fastapi.exceptions import RequestValidationError
from loguru import logger
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.core.config import BASE_CONFIG_DIR, base_path
from app.depends import get_session
from app.ext.sqlmodel_celery_beat.models import PeriodicTask
from app.models.tasks_model import TasksHistory, TaskType
from app.utils.cache_tools import is_json
from app.utils.files_tools import remove_dir


class RunConf(BaseModel):
    """
    base conf
    """

    task_name: Optional[str] = Field(default=None, description="task name")
    task_type: Optional[str] = Field(default=None, description="task type")
    private_data_dir: Optional[str] = Field(
        default=None, description="private data dir"
    )
    inventory: Optional[dict | str] = Field(description="inventory")
    ident: Optional[str] = Field(default=None, description="run id")
    verbosity: Optional[int] = Field(default=None, description="verbosity")
    host_pattern: Optional[str] = Field(default="all", description="host pattern")
    forks: Optional[int] = Field(default=None, description="forks")
    extravars: Optional[dict] = Field(default=None, description="extra vars")
    cmdline: Optional[str] = Field(default=None, description="command line")
    timeout: Optional[int] = Field(default=300, description="timeout")
    rotate_artifacts: Optional[int] = Field(default=0, description="rotate artifacts")
    ssh_key: Optional[str] = Field(default=None, description="ssh key content")
    quiet: Optional[bool] = Field(default=False, description="quiet")
    json_mode: Optional[bool] = Field(default=False, description="json mode")
    exec_worker: Optional[str] = Field(default=None, description="exec worker")
    module: Optional[str] = Field(default=None, description="ansible module")
    module_args: Optional[str] = Field(default=None, description="ansible module args")
    project_dir: Optional[str] = Field(default=None, description="project path")
    playbook: Optional[str] = Field(default=None, description="playbook file")
    tags: Optional[str] = Field(default=None, description="tags")
    skip_tags: Optional[str] = Field(default=None, description="skip tags")
    role: Optional[str] = Field(default=None, description="role name")
    roles_path: Optional[str] = Field(default=None, description="roles path")

    def get_record(self, session: Session) -> TasksHistory:
        db_task_record = session.exec(
            select(TasksHistory).where(TasksHistory.task_id == self.ident)
        ).one_or_none()
        if not db_task_record:
            raise Exception("task record not found")
        return db_task_record

    def update_record(self, update_data: dict) -> TasksHistory:
        session = next(get_session())
        try:
            db_task_record = self.get_record(session)
            db_task_record.sqlmodel_update(update_data)
            session.add(db_task_record)
            session.commit()
            return db_task_record
        except Exception as e:
            logger.error(e)
            session.rollback()
            raise e
        finally:
            session.close()

    def check_runner_kwargs(self, task_kwargs: dict, is_check: bool = False) -> dict:
        private_data_dir = os.path.join(
            base_path.tasks_meta_path, self.private_data_dir
        )
        if is_check:
            print(private_data_dir)
            private_data_dir = f"{private_data_dir}-check"

        if os.path.exists(private_data_dir):
            remove_dir(private_data_dir)
            os.makedirs(private_data_dir)
        else:
            os.makedirs(private_data_dir)
        task_kwargs["private_data_dir"] = private_data_dir
        if "project_dir" in task_kwargs:
            task_kwargs["project_dir"] = os.path.join(
                base_path.tasks_templates_path, self.project_dir
            )
        task_kwargs["envvars"] = {
            "ANSIBLE_CONFIG": f"{os.path.join(BASE_CONFIG_DIR, 'ansible.cfg')}"
        }
        return task_kwargs

    def starting_callback(self) -> dict:

        db_task_record = self.update_record({"exec_worker": self.exec_worker})
        task_kwargs = db_task_record.task_kwargs
        if not task_kwargs:
            raise Exception("task kwargs not found")
        config = self.check_runner_kwargs(task_kwargs)
        return config

    def finished_callback(self, runner):
        end_time = int(time.time())
        self.update_record(
            {
                "task_status": runner.status,
                "task_rc": runner.rc,
                "task_end_time": end_time,
            }
        )

    def failed_callback(self, error: str, rc: int):
        end_time = int(time.time())
        self.update_record(
            {
                "task_status": "failed",
                "task_error": error,
                "task_rc": rc,
                "task_end_time": end_time,
            }
        )

    def status_handler(self, data, runner_config):
        if data["status"] == "running":
            self.update_record(
                {
                    "task_status": "running",
                }
            )

    def run_task(self) -> Any:
        try:
            config = self.starting_callback()
            r = ansible_runner.run(
                **config,
                finished_callback=self.finished_callback,
                status_handler=self.status_handler,
            )
            return "{}: {}".format(r.status, r.rc)
        except Exception as e:
            self.failed_callback(error=str(e), rc=-1)
            logger.error(str(e))
            return "{}: {}".format("failed", -1)

    def config_check(self) -> dict:
        if self.cmdline:
            self.cmdline = f"{self.cmdline} --syntax-check"
        else:
            self.cmdline = "--syntax-check"
        self.inventory = json.dumps(self.inventory)
        config = self.check_runner_kwargs(
            self.model_dump(
                exclude_none=True,
                exclude={
                    "task_name",
                    "task_type",
                    "exec_worker",
                },
            ),
            True,
        )
        try:
            run_conf = RunnerConfig(**config)
            run_conf.prepare()
            rc = 0
            status = "successful"
            stdout = None
            if self.task_type == "Playbook":
                r = Runner(config=run_conf)
                r.run()
                rc = r.rc
                status = r.status
                stdout = r.stdout.read()
                remove_dir(run_conf.private_data_dir)
            return {
                "rc": rc,
                "status": status,
                "task_type": self.task_type,
                "stdout": stdout,
            }
        except Exception as e:
            return {
                "rc": -1,
                "status": "failed",
                "task_type": self.task_type,
                "stdout": str(e),
            }


class TasksRunConfig(RunConf):
    """
    前端请求任务执行配置
    """

    task_name: str = Field(description="task name")
    task_type: TaskType = Field(description="task type")
    task_queue_type: str = Field(default=None, description="任务队列类型")
    task_scheduled_name: Optional[str] = Field(default=None, description="任务计划名称")
    inventory: Optional[dict] = Field(default=None, description="主机清单")
    extravars: Optional[str] = Field(default=None, description="额外变量")
    task_template_id: Optional[str] = Field(default=None, description="任务模版ID")
    task_template_name: Optional[str] = Field(
        default=None, description="任务模版显示名"
    )

    def run_scheduled_task(self, exec_worker: str) -> Any:
        session = next(get_session())
        periodic_task = session.exec(
            select(PeriodicTask).where(PeriodicTask.name == self.task_name)
        ).one_or_none()
        if not periodic_task:
            raise Exception("periodic task not found")
        try:
            self.task_queue_type = periodic_task.queue
            create_task_record(
                session=session, username=periodic_task.user_by, run_conf=self
            )
        except Exception as e:
            raise e
        finally:
            session.close()
        try:
            run_config = RunConf.model_validate(self.model_dump())
            run_config.exec_worker = exec_worker
            res = run_config.run_task()
            return res
        except Exception as e:
            raise e


def parse_task_conf(run_conf: TasksRunConfig) -> TasksRunConfig:
    """
    解析任务执行配置
    """
    time_now = time.strftime("%Y%m%d", time.localtime())
    run_conf.private_data_dir = os.path.join(time_now, run_conf.ident)
    if run_conf.task_type == TaskType.playbook:
        if run_conf.task_template_id and run_conf.task_template_name:
            run_conf.project_dir = run_conf.task_template_id
            run_conf.playbook = run_conf.playbook.replace(f"{run_conf.project_dir}/", "")
    if run_conf.extravars:
        if not is_json(run_conf.extravars):
            raise RequestValidationError("extravars Not json format")
        run_conf.extravars = json.loads(run_conf.extravars)
    # Wait for the cmdb API development to finish
    inventory = {}
    run_conf.inventory = inventory
    return run_conf


def create_task_record(
    session: Session,
    run_conf: TasksRunConfig,
    username: str = None,
) -> TasksHistory:
    task_record = session.exec(
        select(TasksHistory).where(TasksHistory.task_id == run_conf.ident)
    ).one_or_none()
    task_kwargs = run_conf.model_dump(
        exclude_none=True,
        exclude={
            "task_name",
            "task_type",
            "task_queue_type",
            "task_scheduled_name",
            "exec_worker",
            "task_template_id",
            "task_template_name",
        },
    )
    task_kwargs["envvars"] = {"ANSIBLE_CONFIG": "config/ansible.cfg"}

    db_task_record = TasksHistory(
        task_id=run_conf.ident,
        task_name=run_conf.task_name,
        task_type=run_conf.task_type,
        task_queue_type=run_conf.task_queue_type,
        task_scheduled_name=run_conf.task_scheduled_name,
        task_kwargs=task_kwargs,
        task_status="starting",
        task_start_time=int(time.time()),
        task_template_id=run_conf.task_template_id,
        task_template_name=run_conf.task_template_name,
        exec_user=username,
    )
    if not task_record:
        task_record = db_task_record
    else:
        task_record.sqlmodel_update(
            db_task_record.model_dump(exclude_none=True, exclude_unset=True)
        )
    try:
        session.add(task_record)
        session.commit()
        return task_record
    except Exception as e:
        session.rollback()
        raise e
