"""Delete a user to GDPR specifications


    python manage.py gdpr_delete_user guid1

Erroring deletions will be logged and skipped.
"""
import logging
import sys

logger = logging.getLogger(__name__)

from django.db import transaction
from django.core.management.base import BaseCommand
from osf.management.utils import boolean_input
from osf.models import OSFUser

class Command(BaseCommand):
    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='Dry run',
        )
        parser.add_argument('guids', type=str, nargs='+', help='user guid to be deleted')

    def handle(self, *args, **options):
        guids = options.get('guids', None)
        dry_run = options.get('dry_run', False)

        if not boolean_input('About to delete users: {}. yes or no?'.format(' '.join(guids))):
            print('Exiting...')
            sys.exit(1)

        with transaction.atomic():
            for guid in guids:
                try:
                    user = OSFUser.load(guid)
                    user.gdpr_delete()
                    user.save()
                except Exception:
                    logger.exception('Error occurred while deleting user {}'.format(guid))
                    logger.error('Skipping...')
                logger.info('Deleted user: {}'.format(guid))

            if dry_run:
                raise RuntimeError('Dry run -- transaction rolled back.')
