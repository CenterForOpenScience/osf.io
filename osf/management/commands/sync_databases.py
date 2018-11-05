"""Command used to ensure databases are in sync.
This just delegates to other commands such as
"python manage.py migrate".

This makes it easy to add new sync commands to run
with each staging deployment, without having to change
the OSF's helm chart.
"""

import waffle
from django.core.management.base import BaseCommand
from django.core.management import call_command
from osf import features

class Command(BaseCommand):

    def handle(self, *args, **options):
        COMMANDS = [
            # Sync Postgres
            ['migrate'],
        ]
        if waffle.switch_is_active(features.ELASTICSEARCH_METRICS):
            COMMANDS.append(['sync_metrics'])

        for check in COMMANDS:
            call_command(*check)
