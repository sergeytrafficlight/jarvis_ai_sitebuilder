from django.core.management.base import BaseCommand, CommandError
from datetime import datetime, date
import requests
from datetime import datetime, timedelta
from ai.ai import get_expenses

class Command(BaseCommand):
    help = 'Command description'


    def handle(self, *args, **options):
        first_day = date.today().replace(day=1)
        total = get_expenses(first_day.strftime('%Y-%m-%d'))

        print(f"Date from: {first_day} costs: {total}")
