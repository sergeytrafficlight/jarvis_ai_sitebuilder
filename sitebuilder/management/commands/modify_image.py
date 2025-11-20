from django.core.management.base import BaseCommand, CommandError
from core.site_analyzer import SiteAnalyzer
from core.models import SubSiteProject, MyTask, ImageAIEdit, ImageAIEditConversation
from core.task import run_task_geneate_image, run_task_edit_image
from core.task_wrapper import task_edit_image
from core.tools import clone_sub_site
from ai.ai import get_edit_image_conversation, get_edit_image_conversation

class Command(BaseCommand):
    help = 'Command description'

    def add_arguments(self, parser):
        parser.add_argument('image_path', type=str)

    def handle(self, *args, **options):
        image_path = options['image_path']

        parts = image_path.split("/")
        site_id = parts[3]
        sub_site_dir = parts[4]

        rel_path = "/".join(parts[5:])

        print(f"Site id: {site_id}")
        print(f"Dir: {sub_site_dir}")

        sub = SubSiteProject.objects.get(site_id=site_id, dir=sub_site_dir)


        print(f"Site id: {site_id} -> Sub: {sub}")
        print(f"Image path: {image_path} -> {rel_path}")

        image, _ = ImageAIEdit.objects.get_or_create(sub_site=sub, file_path=rel_path)

        prompt = input('Prompt:')
        conv = ImageAIEditConversation.objects.create(
            image_ai_edit=image,
            prompt=prompt,
        )

        task = task_edit_image(sub, conv)

        run_task_edit_image(task)







