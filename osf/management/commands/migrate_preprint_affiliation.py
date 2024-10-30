import datetime
import logging

from django.core.management.base import BaseCommand
from osf.models import Preprint

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Assign affiliations from preprint creators, with optional exclusion by user GUIDs.
    """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--exclude-guids',
            nargs='+',
            dest='exclude_guids',
            help='List of user GUIDs to exclude from affiliation assignment'
        )
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='If true, iterates through preprints without making changes'
        )

    def handle(self, *args, **options):
        start_time = datetime.datetime.now()
        logger.info(f'Script started at: {start_time}')

        exclude_guids = set(options.get('exclude_guids', []))
        dry_run = options.get('dry_run', False)

        if dry_run:
            logger.info('Dry Run mode activated')

        processed_count, updated_count, skipped_count = assign_creator_affiliations_to_preprints(
            exclude_guids=exclude_guids, dry_run=dry_run)

        finish_time = datetime.datetime.now()
        logger.info(f'Script finished at: {finish_time}')
        logger.info(f'Total processed: {processed_count}, Updated: {updated_count}, Skipped: {skipped_count}')
        logger.info(f'Total run time: {finish_time - start_time}')


def assign_creator_affiliations_to_preprints(exclude_guids=None, dry_run=True):
    exclude_guids = exclude_guids or set()
    preprints = Preprint.objects.select_related('creator').all()

    processed_count = updated_count = skipped_count = 0

    for preprint in preprints:
        processed_count += 1
        creator = preprint.creator

        if not creator:
            skipped_count += 1
            continue

        if creator._id in exclude_guids or not creator.affiliated_institutions.exists():
            skipped_count += 1
            continue

        if not dry_run:
            affiliations = [
                preprint.affiliated_institutions.get_or_create(institution=inst)[1]
                for inst in creator.affiliated_institutions.all()
            ]
            updated_count += sum(affiliations)
        else:
            logger.info(f'Dry Run: Would assign {creator.affiliated_institutions.count()} affiliations '
                        f'to preprint <{preprint._id}>')

    return processed_count, updated_count, skipped_count
