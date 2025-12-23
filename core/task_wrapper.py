from logging import Logger

from ai.ai import ai_processor_get_default_config
from core.models import SubSiteProject, MyTask, ImageAIEditConversation
from core.log import *
logger.setLevel(logging.DEBUG)


def task_generate_site_name_classification(sub_site: SubSiteProject, engine_cfg = ai_processor_get_default_config()):

    return MyTask.objects.create(
        sub_site=sub_site,
        type=MyTask.TYPE_GENERATE_NAME,
        ai_engine_config=engine_cfg,
    )

def task_generate_site(sub_site: SubSiteProject, prompt: str):
    payload = {
        'prompt': prompt,
    }
    return MyTask.objects.create(
        sub_site=sub_site,
        type=MyTask.TYPE_GENERATE_SITE,
        data_payload=payload,
    )

def task_copy_site_by_url(sub_site: SubSiteProject, ref_url: str):
    payload = {
        'ref_url': ref_url,
    }
    return MyTask.objects.create(
        sub_site=sub_site,
        type=MyTask.TYPE_COPY_SITE_BY_URL,
        data_payload=payload,
    )

def task_edit_file(sub_site: SubSiteProject, prompt: str, file_path: str):
    payload = {
        'path': file_path,
        'prompt': prompt,
    }
    return MyTask.objects.create(
        sub_site=sub_site,
        type=MyTask.TYPE_EDIT_FILE,
        data_payload=payload,
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

def task_edit_image(sub_site: SubSiteProject, ai_edit_conversation: ImageAIEditConversation):
    task = MyTask.objects.create(
        sub_site=sub_site,
        type=MyTask.TYPE_EDIT_IMAGE,
    )
    ai_edit_conversation.task = task
    ai_edit_conversation.save(update_fields=['task'])
    return task

def task_edit_site(sub_site: SubSiteProject, prompt: str, current_url: str = None, current_rel_path: str = None):
    payload = {
        'prompt': prompt
    }
    if current_url:
        payload['current_url'] = current_url
    if current_rel_path:
        payload['current_rel_path'] = current_rel_path

    task = MyTask.objects.create(
        sub_site=sub_site,
        data_payload=payload,
        type=MyTask.TYPE_EDIT_SITE,
    )
    return task

