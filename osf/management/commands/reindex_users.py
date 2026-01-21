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

    # run the command in batches. if --batch_size not provided, 100 users will be processed per time
    python3 manage.py reindex_users --batch_size=150

"""
class Command(BaseCommand):
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument('--guids', type=str, nargs='+', help='Users to reindex by guid')
        parser.add_argument('--batch_size', type=int, help='Number of users to update per time')
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
        batch_size = options.get('batch_size') or 100

        if dry_run:
            logger.info('[DRY RUN] THIS IS A DRY RUN.')
            return

        if guids:
            users = OSFUser.objects.filter(guids___id__in=guids)
        else:
            users = OSFUser.objects.all()

        for user in users.iterator(chunk_size=batch_size):
            logger.info(f'Reindexing {user._id}...')
            user.update_search()
