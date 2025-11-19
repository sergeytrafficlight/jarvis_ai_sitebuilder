from django.core.management.base import BaseCommand, CommandError
from core.site_analyzer import SiteAnalyzer

class Command(BaseCommand):
    help = 'Command description'

    def add_arguments(self, parser):
        parser.add_argument('path', type=str)

    def handle(self, *args, **options):
        path = options['path']
        print(f"path: {path}")

        analyzer = SiteAnalyzer(path)
        result = analyzer.analyze()
        for file, info in result.items():
            print(file)
            print(info)
            print("----")