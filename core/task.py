import time
from celery import shared_task, Task
from ai.ai import ai_log, ai_log_update
from ai.ai import MODEL_CHATGPT
from core.models import SiteProject, MyTask, SystemPromts
import threading


class BaseTask(Task):
    autoretry_for = (Exception,)
    max_retries = 3
    retry_backoff = True
    retry_backoff_max = 60
    retry_jitter = True

    def on_success(self, retval, task_id, args, kwargs):
        return super().on_success(retval, task_id, args, kwargs)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        return super().on_failure(exc, task_id, args, kwargs, einfo)

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        return super().on_retry(exc, task_id, args, kwargs, einfo)


def run_tasks_serial(q):
    pass

def run_task_generate_name(task: MyTask):
    promt = SystemPromts.objects.get(type=SystemPromts.SP_NAME_BASE).promt
    promt += "\n"
    promt += SystemPromts.objects.get(type=SystemPromts.SP_NAME_CLASSIFICATION).promt
    promt += "\n"
    promt += "Промт (начало)\n"
    promt += task.site.promt
    promt += "Промт (конец)\n"


    log = ai_log(task, MODEL_CHATGPT, promt)





@shared_task(bind=True, base=BaseTask, name="core.generate_site")
def run_tasks(self, site_id: int, prompt: str = "", ref_url: str | None = None):
    site_id = site_id

    # STARTED

    try:

        site = SiteProject.objects.get(id=site_id)
        site.status = SiteProject.STATUS_PROCESSING
        site.save()

        tasks = MyTask.objects.filter(site=site, status='PENDING').order_by('id')

        task_queue_parallel = []
        task_queue_serial = []

        error = False

        for t in tasks:
            if t.type in [
                MyTask.TYPE_GENERATE_SITE,
                MyTask.TYPE_GENERATE_NAME,
            ]:
                task_queue_serial.append(t)
            else:
                raise Exception(f"Unknown task ({t.id}) type {t.type}")

        for t in task_queue_serial:
            t.status = 'STARTED'
            t.save()

            try:
                if t.type == MyTask.TYPE_GENERATE_NAME:
                    run_task_generate_name(t)
                else:
                    raise Exception(f"Unknown task ({t.id}) type {t.type}")
            except Exception as e:
                t.status = 'FAILURE'
                error = True
                t.save()
            else:
                t.status = 'SUCCESS'
                t.save()



        if error:
            site.status = SiteProject.STATUS_ERROR
        else:
            site.status = SiteProject.STATUS_DONE

        site.save()
    except Exception as e:
        pass

    return {"site_id": site_id, "status": "published"}
