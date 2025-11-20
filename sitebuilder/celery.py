import os
from celery import Celery
from celery.signals import worker_ready


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sitebuilder.settings")
app = Celery("sitebuilder")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@worker_ready.connect
def _recover_on_start(sender, **kwargs):
    # Опционально: защитимся от повторного запуска на нескольких воркерах через Redis-лок
    try:
        from django.conf import settings
        import redis
        r = redis.Redis.from_url(settings.CELERY_BROKER_URL)
        # ключ живёт 5 минут — достаточно для старта
        if not r.set("sitebuilder:recover_stuck_tasks_once", 1, nx=True, ex=10):
            return
    except Exception:
        # если редис недоступен — просто пробуем один раз (при одном воркере это ок)
        pass

    from core.task import recover_stuck_tasks
    recover_stuck_tasks.delay()
