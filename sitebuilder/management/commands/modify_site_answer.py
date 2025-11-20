import json
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from core.models import SiteProject, SubSiteProject, MyTask, ImageAIEdit, ImageAIEditConversation, AICommunicationLog
from core.task_wrapper import task_generate_site_name_classification, task_generate_site, task_edit_file, task_edit_image, task_generate_image
from core.task import run_tasks_ex, run_task_generate_site_parse_answer
from core.tools import extract_json_from_text, generate_uniq_subsite_dir_for_site, get_subsite_dir
from core.tools import ProcessFileResult

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('site_id', type=str)

    def handle(self, *args, **options):
        site_id = options['site_id']

        site = SiteProject.objects.get(id=site_id)
        sub = SubSiteProject.objects.latest('created_at')

        print(f"Site: {site} Subsite: {sub}")

        answer_file = 'sitebuilder/management/commands/modify_site_answer.txt'

        with open(answer_file, "r", encoding="utf-8") as f:
            answer = f.read()


        print(f"answer")
        print(answer)
        answer_json = extract_json_from_text(answer)
        answer_json = json.loads(answer_json)

        tasks = []

        AICommunicationLog.objects.filter(task__sub_site=sub).delete()
        MyTask.objects.filter(sub_site=sub).delete()

        for task in answer_json:
            prompt = task['prompt'] or ''
            file_path = task['file_path'] or ''
            if task['engine'] == 'text2text':
                t = task_edit_file(sub, prompt, file_path)
                tasks.append(t)
            elif task['engine'] == 'text2img':

                image, _ = ImageAIEdit.objects.get_or_create(sub_site=sub, file_path=file_path)
                conv = ImageAIEditConversation.objects.create(
                    image_ai_edit=image,
                    prompt=prompt,
                )
                t = task_edit_image(sub, conv)
                tasks.append(t)

            else:
                raise Exception(f"Unknown task engine {task['engine']}")


        print(f"Tasks count: {len(tasks)}")
        run_tasks_ex(sub.id)