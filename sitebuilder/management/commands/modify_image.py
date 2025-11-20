from django.core.management.base import BaseCommand, CommandError
from core.site_analyzer import SiteAnalyzer
from core.models import SubSiteProject, MyTask
from core.task import run_task_geneate_image
from core.tools import clone_sub_site
from ai.ai import get_edit_image_conversation, get_edit_image_conversation

class Command(BaseCommand):
    help = 'Command description'

    def add_arguments(self, parser):
        parser.add_argument('image_path', type=str)

    def handle(self, *args, **options):
        image_path = options['image_path']
        print(f"image_path: {image_path}")

        prompt = input('prompt: ')

        answer = get_edit_image_conversation(prompt, image_path)

        print(f"Done")

        with open(image_path, 'wb') as f:
            f.write(answer.answer)

        print(f"response_id: {answer.response_id}")
        print(f"comment: {answer.comment}")



