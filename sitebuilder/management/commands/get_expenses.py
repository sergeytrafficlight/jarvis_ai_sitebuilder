from django.core.management.base import BaseCommand, CommandError
import requests
from datetime import datetime, timedelta
from ai.chatgpt import get_expenses

class Command(BaseCommand):
    help = 'Command description'


    def handle(self, *args, **options):
        date_from = '2025-11-01'
        total = get_expenses(date_from)

        print(f"Date from: {date_from} costs: {total}")
