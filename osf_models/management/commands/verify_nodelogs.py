from __future__ import print_function
from __future__ import unicode_literals

from datetime import datetime

from django.core.management.base import BaseCommand
from osf_models.scripts.verify_nodelogs import main as verify_nodelogs

from website.app import init_app


class Command(BaseCommand):
    help = 'Migrates data from tokumx to postgres'

    def handle(self, *args, **options):
        print('Initializing Flask App...')
        init_app()
        start = datetime.now()

        # verify nodelogs
        verify_nodelogs()

        print('Finished in {} seconds...'.format((datetime.now() - start
                                                  ).total_seconds()))
