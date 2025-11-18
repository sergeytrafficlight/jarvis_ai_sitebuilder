import time
from celery import shared_task, Task
from ai.ai import ai_log, ai_log_update
from core.models import SiteProject, MyTask, SystemPrompts
from ai.ai import get_text2text_answer
from core.tools import generate_uniq_site_dir_for_user, extract_json_from_text, process_file_operations
import threading

from core.log import *
logger.setLevel(logging.DEBUG)



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

    prompt = SystemPrompts.objects.get(type=SystemPrompts.SP_NAME_BASE).prompt
    prompt += "\n"
    prompt += SystemPrompts.objects.get(type=SystemPrompts.SP_NAME_CLASSIFICATION).prompt
    prompt += "\n"
    prompt += "Промт (начало)\n"
    prompt += task.site.prompt
    prompt += "Промт (конец)\n"

    log = ai_log(task, prompt)

    answer = get_text2text_answer(prompt)

    ai_log_update(log, answer)

def run_task_generate_site(task: MyTask):
    prompt = SystemPrompts.objects.get(type=SystemPrompts.SP_NAME_BASE).prompt
    prompt += "\n"
    prompt += SystemPrompts.objects.get(type=SystemPrompts.SP_NAME_BASE_JSON).prompt
    prompt += "\nЗапрос пользователя для генерации html сайта:\n"
    prompt += task.site.prompt

    log = ai_log(task, prompt)

    answer = get_text2text_answer(prompt)

    dir = generate_uniq_site_dir_for_user(task.site.user)

    ai_log_update(log, answer)

    answer_json = extract_json_from_text(answer.answer)
    logger.debug(f"Dir {dir}")
    result = process_file_operations(answer_json, dir)
    if result['success'] != True:
        raise Exception(f"Can't proceed file operations")
    for e in result['errors']:
        logger.debug(f" error: {str(e)}")




def run_tasks_ex(site_id: int):
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
                elif t.type == MyTask.TYPE_GENERATE_SITE:
                    run_task_generate_site(t)
                else:
                    raise Exception(f"Unknown task ({t.id}) type {t.type}")
            except Exception as e:
                logger.debug(f"error: {e}")
                logger.error("Exception occurred:\n%s", traceback.format_exc())
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
        logger.debug(f"error: {e}")
        logger.error("Exception occurred:\n%s", traceback.format_exc())

    return {"site_id": site_id, "status": "published"}


@shared_task(bind=True, base=BaseTask, name="core.generate_site")
def run_tasks(self, site_id: int):
    return run_tasks_ex(site_id)