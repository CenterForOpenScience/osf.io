"""Command used to ensure databases are in sync.
This just delegates to other commands such as
"python manage.py migrate".

This makes it easy to add new sync commands to run
with each staging deployment, without having to change
the OSF's helm chart.
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command


COMMANDS = [
    # Sync Postgres
    ['migrate'],
    # Sync Elasticsearch index templates
    ['sync_metrics'],
]

class Command(BaseCommand):

    def handle(self, *args, **options):
        for check in COMMANDS:
            call_command(*check)
