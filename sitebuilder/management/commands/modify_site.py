from django.core.management.base import BaseCommand, CommandError
from core.site_analyzer import SiteAnalyzer
from core.models import SubSiteProject, MyTask, ImageAIEdit, ImageAIEditConversation, SiteProject
from core.task import run_task_geneate_image, run_task_edit_image, run_task_edit_site
from core.task_wrapper import task_edit_image, task_edit_site
from core.tools import clone_sub_site
from ai.ai import get_edit_image_conversation, get_edit_image_conversation

class Command(BaseCommand):
    help = 'Command description'

    def add_arguments(self, parser):
        parser.add_argument('site_id', type=str)

    def handle(self, *args, **options):
        site_id = options['site_id']

        site = SiteProject.objects.get(id=site_id)
        sub = SubSiteProject.objects.latest('created_at')

        print(f"Site: {site} Subsite: {sub}")

        prompt = input("prompt: ")

        task = task_edit_site(sub, prompt)
        run_task_edit_site(task)










