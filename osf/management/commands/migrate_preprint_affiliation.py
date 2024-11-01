import datetime
import logging

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F, Exists, OuterRef

from osf.models import PreprintContributor, InstitutionAffiliation

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Assign affiliations from users to preprints where they have write or admin permissions, with optional exclusion by user GUIDs."""

    help = 'Assign affiliations from users to preprints where they have write or admin permissions.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--exclude-guids',
            nargs='+',
            dest='exclude_guids',
            help='List of user GUIDs to exclude from affiliation assignment'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            help='If true, performs a dry run without making changes'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            dest='batch_size',
            help='Number of contributors to process in each batch'
        )

    def handle(self, *args, **options):
        start_time = datetime.datetime.now()
        logger.info(f'Script started at: {start_time}')

        exclude_guids = set(options.get('exclude_guids') or [])
        dry_run = options.get('dry_run', False)
        batch_size = options.get('batch_size', 1000)

        if dry_run:
            logger.info('Dry run mode activated.')

        processed_count, updated_count = assign_affiliations_to_preprints(
            exclude_guids=exclude_guids,
            dry_run=dry_run,
            batch_size=batch_size
        )

        finish_time = datetime.datetime.now()
        logger.info(f'Script finished at: {finish_time}')
        logger.info(f'Total processed: {processed_count}, Updated: {updated_count}')
        logger.info(f'Total run time: {finish_time - start_time}')


def assign_affiliations_to_preprints(exclude_guids=None, dry_run=True, batch_size=1000):
    exclude_guids = exclude_guids or set()
    processed_count = updated_count = 0

    # Subquery to check if the user has any affiliated institutions
    user_has_affiliations = Exists(
        InstitutionAffiliation.objects.filter(
            user=OuterRef('user')
        )
    )

    contributors_qs = PreprintContributor.objects.filter(
        preprint__preprintgroupobjectpermission__permission__codename__in=['write_preprint', 'admin_preprint'],
        preprint__preprintgroupobjectpermission__group__user=F('user'),
    ).filter(
        user_has_affiliations
    ).select_related(
        'user',
        'preprint'
    ).exclude(
        user__guids___id__in=exclude_guids
    ).order_by('pk')  # Ensure consistent ordering for batching

    total_contributors = contributors_qs.count()
    logger.info(f'Total contributors to process: {total_contributors}')

    # Process contributors in batches
    with transaction.atomic():
        for offset in range(0, total_contributors, batch_size):
            # Use select_for_update() to ensure query hits the primary database
            batch_contributors = contributors_qs[offset:offset + batch_size].select_for_update()

            logger.info(f'Processing contributors {offset + 1} to {min(offset + batch_size, total_contributors)}')

            for contributor in batch_contributors:
                user = contributor.user
                preprint = contributor.preprint

                user_institutions = user.get_affiliated_institutions()
                processed_count += 1
                if not dry_run:
                    preprint.affiliated_institutions.add(*user_institutions)
                    updated_count += 1
                    logger.info(
                        f'Assigned {len(user_institutions)} affiliations from user <{user._id}> to preprint <{preprint._id}>.'
                    )
                else:
                    logger.info(
                        f'Dry run: Would assign {len(user_institutions)} affiliations from user <{user._id}> to preprint <{preprint._id}>.'
                    )

    return processed_count, updated_count
