from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from core.models import SiteProject
from core.task_wrapper import task_generate_site_name_classification, task_generate_site
from core.task import run_tasks_ex
from core.tools import extract_json_from_text, generate_uniq_site_dir_for_user, process_file_operations

class Command(BaseCommand):

    def handle(self, *args, **options):

        user = User.objects.get(is_superuser=1)

        dir = generate_uniq_site_dir_for_user(user)

        print(f"dir: {dir}")

        answer_file = 'sitebuilder/management/commands/generate_test_site_answer.txt'

        with open(answer_file, "r", encoding="utf-8") as f:
            answer = f.read()

        answer_json = extract_json_from_text(answer)
        result = process_file_operations(answer_json, dir)
        print(f"Success: {result['success']}")
        for e in result['errors']:
            print(f" error: {str(e)}")

        for img in result['imgs']:
            print(f"Images: {img[0]} : {img[1]}")