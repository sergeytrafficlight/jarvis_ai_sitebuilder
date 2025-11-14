import time
from celery import shared_task, Task
from core.models import SiteProject, MyTask


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


@shared_task(bind=True, base=BaseTask, name="core.generate_site")
def generate_site(self, site_id: int, prompt: str = "", ref_url: str | None = None):
    task_id = self.request.id

    # STARTED
    try:
        mt = MyTask.objects.get(task_id=task_id)
        mt.status = "STARTED"
        mt.save(update_fields=["status", "updated_at"])
    except MyTask.DoesNotExist:
        pass

    site = SiteProject.objects.get(id=site_id)

    # Эмуляция работы
    time.sleep(2)

    # Считаем, что сайт сгенерирован
    site.status = SiteProject.STATUS_PUBLISHED
    site.save(update_fields=["status"])

    # SUCCESS
    try:
        mt = MyTask.objects.get(task_id=task_id)
        mt.status = "SUCCESS"
        mt.message = "Site published"
        mt.save(update_fields=["status", "message", "updated_at"])
    except MyTask.DoesNotExist:
        pass

    return {"site_id": site_id, "status": "published"}
