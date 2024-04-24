from app.ext.ansible_tsk.runner import RunConf, TasksRunConfig, parse_task_conf
from app.tasks import celery


@celery.task(name="tasks.asb_temp_task", bind=True, rate_limit="30/m")
def asb_temp_task(self, **kwargs):
    run_config = RunConf.model_validate(kwargs)
    run_config.exec_worker = self.request.hostname
    res = run_config.run_task()
    return res


@celery.task(name="tasks.asb_scheduled_task", bind=True, rate_limit="30/m")
def asb_scheduled_task(self, **kwargs):
    task_config = TasksRunConfig.model_validate(kwargs)
    task_config.ident = str(self.request.id)
    task_run_conf = parse_task_conf(task_config)
    res = task_run_conf.run_scheduled_task(self.request.hostname)
    return res
