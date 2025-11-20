import time
import json
import requests
import threading
from celery import shared_task, Task
from ai.ai import ai_log, ai_log_update
from core.models import SiteProject, MyTask, SystemPrompts, SubSiteProject
from ai.ai import get_text2text_answer, get_text2img_answer
from core.tools import get_subsite_dir, extract_json_from_text
from core.tools import ProcessFileResult
from django.urls import reverse
from core.task_wrapper import task_generate_image
from config import THREADS_PARALLEL_MAX_COUNT, SITE_URL
from core.screenshot import generate_screenshort
from core.site_analyzer import SiteAnalyzer
from core.funds_balance import charge

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



def run_task_generate_name(task: MyTask):

    prompt = SystemPrompts.objects.get(type=SystemPrompts.SP_NAME_BASE).prompt
    prompt += "\n"
    prompt += SystemPrompts.objects.get(type=SystemPrompts.SP_NAME_CLASSIFICATION).prompt
    prompt += "\n"
    prompt += "Промт (начало)\n"
    prompt += task.sub_site.site.prompt
    prompt += "Промт (конец)\n"

    logger.debug(f'Generate site name')
    log = ai_log(task, prompt)

    answer = get_text2text_answer(prompt, creative_enabled=True)

    ai_log_update(log, answer)

    task.sub_site.site.name = answer.answer
    task.sub_site.site.save(update_fields=['name'])

    charge(task.sub_site, answer, task.type)

    logger.debug(f"Done: {answer.answer}")


def run_task_generate_site_parse_answer(task: MyTask, answer: str):
    dir = get_subsite_dir(task.sub_site)
    logger.debug(f"Dir: {dir}")
    #logger.debug(f"answer: {answer}")
    answer_json = extract_json_from_text(answer)
    #logger.debug(answer_json)

    result = ProcessFileResult()
    if result.process_file_operations(answer_json, dir):
        logger.debug(f"Done")
    else:
        for e in result.errors:
            logger.debug(f"error: {e}")

    for f in result.files:
        t = f.type()
        if t == ProcessFileResult.File.TYPE_TEXT:
            pass
        elif t == ProcessFileResult.File.TYPE_IMG:
            task_generate_image(task.sub_site, f.path, f.prompt)
        else:
            raise Exception(f"Unknown file type {t}")

    return result

def run_task_generate_site(task: MyTask):
    prompt = SystemPrompts.objects.get(type=SystemPrompts.SP_NAME_BASE).prompt
    prompt += "\n"
    prompt += SystemPrompts.objects.get(type=SystemPrompts.SP_NAME_BASE_JSON).prompt
    prompt += "\nЗапрос пользователя для генерации html сайта:\n"
    prompt += task.sub_site.site.prompt

    log = ai_log(task, prompt)

    logger.debug(f"generate site strucutre")
    answer = get_text2text_answer(prompt)
    logger.debug(f"done")

    logger.debug(f"Dir {dir}")

    charge(task.sub_site, answer, task.type)
    ai_log_update(log, answer)

    run_task_generate_site_parse_answer(task, answer.answer)



def run_task_geneate_image(task: MyTask):

    logger.debug(f"generate image, task: {task.id}")
    #logger.debug(f"payload: {task.data_payload}")

    if not task.data_payload:
        raise Exception(f"Empty data payload")


    file_path = task.data_payload['path']
    img_prompt = task.data_payload['prompt']

    logger.debug(f"file path: {file_path}")

    path_site = get_subsite_dir(task.sub_site)
    sa = SiteAnalyzer(path_site)
    sa.analyze()

    rel_files = sa.get_related_files(file_path)

    for rel in rel_files:
        logger.debug(f"{file_path} -> {rel}")

    rel_file = None
    screenshot_path = None
    html_text = None

    if len(rel_files):
        rel_file = rel_files[0]

    if rel_file:
        rel_file_path = get_subsite_dir(task.sub_site) + f"/{rel_file}"
        with open(rel_file_path, 'r') as f:
            html_text = f.read()

        url = SITE_URL + "/" + get_subsite_dir(task.sub_site)
        url += f"/{rel_file}"

        logger.debug(f"generate screenshot for {rel_file} on url: {url}")
        r, result = generate_screenshort(task.sub_site.site.user, url, task.sub_site.site.user)
        if not result:
            raise Exception(f"Can't generate screenshot for {url}")
        logger.debug(f"screenshot received: {result.image.url}")
        screenshot_path = result.image.url
        if screenshot_path.startswith("/"):
            screenshot_path = screenshot_path[1:]

    else:
        logger.debug(f"working without screenshot")

    prompt = SystemPrompts.objects.get(type=SystemPrompts.SP_NAME_BASE).prompt
    prompt += SystemPrompts.objects.get(type=SystemPrompts.SP_NAME_GENERATE_FOR_SITE_IMAGE).prompt
    if screenshot_path:
        prompt += SystemPrompts.objects.get(type=SystemPrompts.SP_NAME_I_HAVE_PAGE_SCREENSHOT).prompt
        prompt += f"\n{html_text}"

    prompt += f"\n{img_prompt}"
    prompt += f"\nпуть к файлу: {file_path}"

    log = ai_log(task, prompt)
    answer = get_text2img_answer(prompt=prompt,input_image_path=screenshot_path, creative_enabled=True)
    file_path = get_subsite_dir(task.sub_site) + "/" + file_path
    with open(file_path, "wb") as f:
        f.write(answer.answer)

    charge(task.sub_site, answer, task.type)
    ai_log_update(log, answer)



class ParallelTasks:

    def __init__(self):
        self.tasks = []
        self.error = False
        self.lock = threading.Lock()


    def set_error(self):
        with self.lock:
            if not self.error:
                self.error = True

    def get_task(self):
        with self.lock:
            if not self.tasks:
                return None
            return self.tasks.pop(0)



def run_tasks_ex_thread(tasks):

    while True:
        t = tasks.get_task()
        if not t:
            return None

        t.status = MyTask.STATUS_PROCESSING
        t.save()

        try:
            if t.type == MyTask.TYPE_GENERATE_IMAGE:
                run_task_geneate_image(t)
            else:
                raise Exception(f"Unknown task type {t.type}")
        except Exception as e:
            t.status = MyTask.STATUS_ERROR
            t.error = str(e)
            t.save()
            continue

        t.status = MyTask.STATUS_DONE
        t.save()


def run_tasks_ex_cycle(sub_site_id: int):
    sub_site_id = sub_site_id

    logger.debug(f"run for {sub_site_id}")

    try:

        sub_site = SubSiteProject.objects.get(id=sub_site_id)

        logger.debug(f"subsite: {sub_site}")

        sub_site.status = SubSiteProject.STATUS_PROCESSING
        sub_site.save()

        tasks = MyTask.objects.filter(sub_site=sub_site, status=MyTask.STATUS_AWAITING).order_by('id')
        logger.debug(f"tasks count: {tasks.count()}")

        tasks_count = tasks.count()


        task_queue_parallel = ParallelTasks()
        task_queue_serial = []

        error = False

        for t in tasks:
            if t.type in [
                MyTask.TYPE_GENERATE_SITE,
                MyTask.TYPE_GENERATE_NAME,
            ]:
                task_queue_serial.append(t)
            elif t.type in [
                MyTask.TYPE_GENERATE_IMAGE
            ]:
                task_queue_parallel.tasks.append(t)
            else:
                raise Exception(f"Unknown task ({t.id}) type {t.type}")

        for t in task_queue_serial:
            t.status = MyTask.STATUS_PROCESSING
            t.save()

            try:
                if t.type == MyTask.TYPE_GENERATE_NAME:
                    run_task_generate_name(t)
                elif t.type == MyTask.TYPE_GENERATE_SITE:
                    run_task_generate_site(t)
                else:
                    raise Exception(f"Unknown task ({t.id}) type {t.type}")

                t.status = MyTask.STATUS_DONE
                t.save()
            except Exception as e:
                logger.debug(f"error: {e}")
                logger.error("Exception occurred:\n%s", traceback.format_exc())
                t.status = MyTask.STATUS_ERROR
                t.error = str(e)
                error = True
                t.save()
                break
            else:
                t.status = MyTask.STATUS_DONE
                t.error = ''
                t.save()


        threads_count = THREADS_PARALLEL_MAX_COUNT
        if len(task_queue_parallel.tasks) < threads_count:
            threads_count = len(task_queue_parallel.tasks)

        threads = []
        for i in range(threads_count):
            t = threading.Thread(target=run_tasks_ex_thread, args=(task_queue_parallel, ))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        if error:
            sub_site.status = SubSiteProject.STATUS_ERROR
        else:
            sub_site.status = SubSiteProject.STATUS_DONE

        sub_site.save()
    except Exception as e:
        logger.debug(f"error: {e}")
        logger.error("Exception occurred:\n%s", traceback.format_exc())
        return 0

    return tasks_count


def run_tasks_ex(sub_site_id: int):
    while run_tasks_ex_cycle(sub_site_id) != 0:
        pass

@shared_task(bind=True, base=BaseTask, name="core.generate_site")
def run_tasks(self, sub_site_id: int):
    return run_tasks_ex(sub_site_id)