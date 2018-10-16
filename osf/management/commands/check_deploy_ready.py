"""Command used to prevent pods from failing over until
databases are in sync. This just delegates to other
mgmt commands and returns a non-zero exit code if
any of them error.
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command


CHECKS = [
    ['checkmigrations'],
]

class Command(BaseCommand):

    def handle(self, *args, **options):
        for check in CHECKS:
            call_command(*check)
