from django.core.management.base import BaseCommand, CommandError
from core.site_analyzer import SiteAnalyzer
from core.models import SubSiteProject, MyTask
from core.task import run_task_geneate_image
from core.tools import clone_sub_site

class Command(BaseCommand):
    help = 'Command description'

    def add_arguments(self, parser):
        parser.add_argument('site_id', type=str)

    def handle(self, *args, **options):
        site_id = options['site_id']
        print(f"site_id: {site_id}")

        sub_site = SubSiteProject.objects.filter(site_id=site_id).first()
        print(f"sub site: {sub_site}")

        prompt_file = 'sitebuilder/management/commands/modify_task.txt'

        new_sub_site = clone_sub_site(sub_site)







