import datetime
import logging

from django.core.management.base import BaseCommand
from django.db import transaction
from osf.models import PreprintContributor
from django.db.models import F, Count

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

    def handle(self, *args, **options):
        start_time = datetime.datetime.now()
        logger.info(f'Script started at: {start_time}')

        exclude_guids = set(options.get('exclude_guids') or [])
        dry_run = options.get('dry_run', False)

        if dry_run:
            logger.info('Dry run mode activated.')

        processed_count, updated_count, skipped_count = assign_affiliations_to_preprints(
            exclude_guids=exclude_guids,
            dry_run=dry_run
        )

        finish_time = datetime.datetime.now()
        logger.info(f'Script finished at: {finish_time}')
        logger.info(f'Total processed: {processed_count}, Updated: {updated_count}, Skipped: {skipped_count}')
        logger.info(f'Total run time: {finish_time - start_time}')


def assign_affiliations_to_preprints(exclude_guids=None, dry_run=True):
    exclude_guids = exclude_guids or set()
    contributors = PreprintContributor.objects.filter(
        preprint__preprintgroupobjectpermission__permission__codename__in=['write_preprint', 'admin_preprint'],
        preprint__preprintgroupobjectpermission__group__user=F('user'),
    ).annotate(
        num_affiliations=Count('user__institutionaffiliation')
    ).filter(
        num_affiliations__gt=0  # Exclude users with no affiliations
    ).select_related(
        'user',
        'preprint'
    ).exclude(
        user__guids___id__in=exclude_guids
    ).distinct()

    processed_count = updated_count = skipped_count = 0

    with transaction.atomic():
        for contributor in contributors:
            user = contributor.user
            preprint = contributor.preprint

            user_institutions = set(user.get_affiliated_institutions())
            preprint_institutions = set(preprint.affiliated_institutions.all())

            new_institutions = user_institutions - preprint_institutions

            if new_institutions:
                processed_count += 1
                if not dry_run:
                    for institution in new_institutions:
                        preprint.affiliated_institutions.add(institution)
                    updated_count += 1
                    logger.info(
                        f'Assigned {len(new_institutions)} affiliations from user <{user._id}> to preprint <{preprint._id}>.'
                    )
                else:
                    logger.info(
                        f'Dry run: Would assign {len(new_institutions)} affiliations from user <{user._id}> to preprint <{preprint._id}>.'
                    )
            else:
                skipped_count += 1

    return processed_count, updated_count, skipped_count
