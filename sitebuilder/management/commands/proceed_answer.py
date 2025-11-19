from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from core.models import SiteProject, SubSiteProject, MyTask
from core.task_wrapper import task_generate_site_name_classification, task_generate_site
from core.task import run_tasks_ex, run_task_generate_site_parse_answer
from core.tools import extract_json_from_text, generate_uniq_subsite_dir_for_site, get_subsite_dir
from core.tools import ProcessFileResult

class Command(BaseCommand):

    def handle(self, *args, **options):

        user = User.objects.get(is_superuser=1)

        site = SiteProject.objects.create(
            user = user,
            name = f"test console",
        )

        full_path, uniq_dir = generate_uniq_subsite_dir_for_site(site)

        sub_site = SubSiteProject.objects.create(
            site=site,
            root_sub_site=None,
            dir = uniq_dir,
        )

        task = MyTask.objects.create(
            sub_site=sub_site,
            type=MyTask.TYPE_GENERATE_SITE,
        )



        answer_file = 'sitebuilder/management/commands/generate_test_site_answer.txt'

        with open(answer_file, "r", encoding="utf-8") as f:
            answer = f.read()

        result = run_task_generate_site_parse_answer(task, answer)

        print(f"Result: {not len(result.errors)}")
        print(f"Errors: {len(result.errors)}")
        for e in result.errors:
            print(f"Error: {e}")
        print(f"Files: {len(result.files)}")
        for f in result.files:
            s = f.info()
            print(f"File: {s}")
