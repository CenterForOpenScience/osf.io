import logging
from django.core.management.base import BaseCommand
from django.db.models import Q

from osf.models import OSFUser

logger = logging.getLogger(__name__)

AUTHORIZED_EMAIL_SUFFIX = '@cos.io'


def get_unauthorized_users():
    """Return active users with no cos.io username or email address."""
    authorized_ids = OSFUser.objects.filter(
        Q(username__iendswith=AUTHORIZED_EMAIL_SUFFIX)
    ).values('id')
    return OSFUser.objects.filter(
        date_disabled__isnull=True
    ).exclude(id__in=authorized_ids)


def disable_unauthorized_users(dry_run=False, batch_size=1000):
    """Disable active users without a cos.io address, selecting and disabling `batch_size` users at a time."""
    unauthorized = get_unauthorized_users().order_by('id')

    total_count = unauthorized.count()
    logger.info(f'{"[DRY RUN] " if dry_run else ""}Found {total_count} users without a cos.io email address')

    if total_count == 0:
        logger.info('No users to disable')
        return 0

    if dry_run:
        processed = 0
        for user in unauthorized.iterator(chunk_size=batch_size):
            processed += 1
            logger.info(f'[DRY RUN] Would disable user {user._id} [{processed}/{total_count}]')
        logger.info(f'[DRY RUN] Completed. Would disable {processed} users')
        return processed

    processed = 0
    failed_ids = []
    while True:
        batch = list(unauthorized.exclude(id__in=failed_ids)[:batch_size])
        if not batch:
            break

        for user in batch:
            try:
                user.deactivate_account()
                user.save()
                processed += 1
            except Exception as e:
                failed_ids.append(user.id)
                logger.error(f'Failed to disable user {user._id}: {e}')

        logger.info(f'Disabled batch of {len(batch)} users ({processed}/{total_count})')

    summary = f'Completed. Disabled {processed} users'
    if failed_ids:
        summary += f', {len(failed_ids)} failed'
    logger.info(summary)
    return processed


class Command(BaseCommand):
    help = 'Disable active users who have no cos.io email address.'

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            help='Preview which users would be disabled without making changes',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            dest='batch_size',
            help='Number of users to select and disable in each batch (default: 1000)',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        batch_size = options.get('batch_size', 1000)

        if dry_run:
            logger.info('=' * 60)
            logger.info('DRY RUN MODE - No changes will be made')
            logger.info('=' * 60)

        disable_unauthorized_users(dry_run=dry_run, batch_size=batch_size)
