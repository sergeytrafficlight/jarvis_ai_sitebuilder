from django.core.management.base import BaseCommand, CommandError
from core.site_analyzer import SiteAnalyzer
from core.models import SubSiteProject, MyTask, ImageAIEdit, ImageAIEditConversation
from core.task import run_task_geneate_image, run_task_edit_image
from core.task_wrapper import task_edit_image
from core.tools import clone_sub_site
from ai.ai import get_edit_image_conversation, get_edit_image_conversation
from ai.chatgpt import calculate_gpt5_image_tokens

class Command(BaseCommand):
    help = 'Command description'

    def add_arguments(self, parser):
        parser.add_argument('image_path', type=str)

    def handle(self, *args, **options):
        image_path = options['image_path']

        tokens = calculate_gpt5_image_tokens(image_path)
        print(f"Path: {image_path}")
        print(f"Tokens: {tokens}")