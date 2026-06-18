from django.core.management.base import BaseCommand

from agro.services.schemes import ensure_schemes_in_db


class Command(BaseCommand):
    help = 'Load government schemes from schemes_india.json into the database'

    def handle(self, *args, **options):
        count = ensure_schemes_in_db()
        self.stdout.write(self.style.SUCCESS(f'Schemes ready: {count} records in database'))
