"""Delete a user to GDPR specifications


    python3 manage.py gdpr_delete_user guid1

Erroring deletions will be logged and skipped.
"""
import logging
import sys

from django.db import transaction
from django.core.management.base import BaseCommand
from osf.management.utils import ask_for_confirmation
from osf.models import OSFUser

logger = logging.getLogger(__name__)

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

        if not ask_for_confirmation(
            'About to delete user(s): {}. yes or no?'.format(' '.join(guids))
        ):
            print('Exiting...')
            sys.exit(1)

        with transaction.atomic():
            for guid in guids:
                user = OSFUser.load(guid)
                user.gdpr_delete()
                user.save()
                logger.info('Deleted user {}'.format(user._id))
            if dry_run:
                raise RuntimeError('Dry run -- transaction rolled back.')
