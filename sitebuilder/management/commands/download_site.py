from django.core.management.base import BaseCommand, CommandError
from core.downloader import Downloader

class Command(BaseCommand):
    help = 'Command description'


    def handle(self, *args, **options):
        url = 'https://arterotonic.xcartpro.com/r1/?off=vvD4cMwq&lnk=85871&m=e993a8416c7af'
        dir = 'test_dir/downloaded_site/'

        d = Downloader(url, dir)
        d.download()

