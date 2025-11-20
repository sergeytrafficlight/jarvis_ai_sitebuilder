from django.core.management.base import BaseCommand, CommandError
from core.site_analyzer import SiteAnalyzer
from core.models import SubSiteProject, MyTask
from core.task import run_tasks_ex
from core.tools import clone_sub_site
from ai.ai import get_edit_image_conversation, get_edit_image_conversation

class Command(BaseCommand):
    help = 'Command description'

    def add_arguments(self, parser):
        parser.add_argument('sub_site_id', type=str)

    def handle(self, *args, **options):

        sub_site_id = options['sub_site_id']
        print(f"sub_site_id: {sub_site_id}")

        sub = SubSiteProject.objects.get(id=sub_site_id)

        print(f"Sub: {sub}")

        MyTask.objects.filter(sub_site=sub, status__in=[MyTask.STATUS_ERROR]).update(status=MyTask.STATUS_AWAITING)



        qs = MyTask.objects.filter(sub_site=sub, status__in=[MyTask.STATUS_AWAITING])
        print(f"Tasks count: {qs.count()}")

        for t in qs:
            print(f"Run task: {t.id} {t.status} {t.type}")
            run_tasks_ex(t.sub_site.id)





