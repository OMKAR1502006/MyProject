"""Sync live mandi prices from data.gov.in into local cache (requires AGMARKNET_API_KEY)."""

from django.core.management.base import BaseCommand

from agro.services.market import sync_mandi_cache


class Command(BaseCommand):
    help = 'Fetch Agmarknet mandi prices via data.gov.in and cache locally for offline use.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=500, help='Max records to fetch')

    def handle(self, *args, **options):
        result = sync_mandi_cache(limit=options['limit'])
        if result.get('ok'):
            self.stdout.write(
                self.style.SUCCESS(
                    f"Cached {result['count']} mandi records (API total: {result.get('total', 'n/a')})"
                )
            )
        else:
            self.stdout.write(self.style.WARNING(result.get('error', 'Sync failed')))
