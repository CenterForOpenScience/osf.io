"""Resend all resources (nodes, registrations, preprints) for given providers to SHARE."""
import logging

from django.core.management.base import BaseCommand
from osf.models import OSFUser


logger = logging.getLogger(__name__)


"""
Usage:

    # run the command in a dry-run mode
    python3 manage.py reindex_users --dry

    # run the command for specific users. if --guids not provided, all users will be reindexed
    python3 manage.py reindex_users --guids abc12 qwe34

"""
class Command(BaseCommand):
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument('--guids', type=str, nargs='+', help='Users to reindex by guid')
        parser.add_argument(
            '-d',
            '--dry',
            action='store_true',
            dest='dry_run',
            help='Dry mode',
        )

    def handle(self, *args, **options):
        guids = options.get('guids') or []
        dry_run = options.get('dry_run', True)

        if dry_run:
            logger.info('[DRY RUN] THIS IS A DRY RUN.')
            return

        if guids:
            users = OSFUser.objects.filter(guids___id__in=guids)
        else:
            users = OSFUser.objects.all()

        for user in users:
            logger.info(f'Reindexing {user._id}...')
            user.update_search()
