from logging import Logger

from core.models import SubSiteProject, MyTask
from core.log import *
logger.setLevel(logging.DEBUG)


def task_generate_site_name_classification(sub_site: SubSiteProject):

    return MyTask.objects.create(
        sub_site=sub_site,
        type=MyTask.TYPE_GENERATE_NAME,
    )

def task_generate_site(sub_site: SubSiteProject):
    return MyTask.objects.create(
        sub_site=sub_site,
        type=MyTask.TYPE_GENERATE_SITE,
    )

def task_generate_image(sub_site: SubSiteProject, path: str, prompt: str):
    payload = {
        'path': path,
        'prompt': prompt,
    }
    return MyTask.objects.create(
        sub_site=sub_site,
        type=MyTask.TYPE_GENERATE_IMAGE,
        data_payload=payload,
    )

