from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from core.models import SiteProject
from core.task_wrapper import task_generate_site_name_classification, task_generate_site
from core.task import run_tasks_ex

class Command(BaseCommand):

    def handle(self, *args, **options):

        user = User.objects.get(is_superuser=1)

        prompt_file = 'sitebuilder/management/commands/generate_test_site_prompt.txt'

        with open(prompt_file, "r", encoding="utf-8") as f:
            prompt = f.read()

        site = SiteProject.objects.create(
            user = user,
            name = f"test console",
            prompt = prompt,
        )

        task_generate_site_name_classification(site)
        task_generate_site(site)

        run_tasks_ex(site.id)




