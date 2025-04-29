from django.core.management.base import BaseCommand
from django.db.models import Q
from osf.models import Preprint, Guid
import logging

logger = logging.getLogger(__name__)


def process_wrong_why_not_data_preprints(
        version_guid: str | None,
        dry_run: bool,
        executing_through_command: bool = True,
        command_obj: BaseCommand = None
):
    through_command_constrain = executing_through_command and command_obj
    why_no_data_filters = Q(why_no_data__isnull=False) & ~Q(why_no_data='')

    if version_guid:
        base_guid_str, version = Guid.split_guid(version_guid)
        preprints = Preprint.objects.filter(
            versioned_guids__guid___id=base_guid_str,
            versioned_guids__version=version
        )
        if not preprints:
            no_preprint_message = f'No preprint found with version_guid: {version_guid}'
            logger.error(no_preprint_message)
            if through_command_constrain:
                command_obj.stdout.write(command_obj.style.ERROR(no_preprint_message))
            return
        if preprints[0].has_data_links != 'no' and not preprints[0].why_no_data:
            correct_behavior_message = f'Correct behavior for {preprints[0]._id} has_data_links={preprints[0].has_data_links} why_no_data={preprints[0].why_no_data}'
            if through_command_constrain:
                command_obj.stdout.write(correct_behavior_message)
            return

    else:
        preprints = Preprint.objects.filter(
            ~Q(has_data_links='no') & why_no_data_filters
        )

    total = preprints.count()
    logger.info(f'Found {total} preprints to process')
    if through_command_constrain:
        command_obj.stdout.write(f'Found {total} preprints to process')

    processed = 0
    errors = 0

    for preprint in preprints:
        try:
            logger.info(f'Processing preprint {preprint._id}')
            if through_command_constrain:
                command_obj.stdout.write(f'Processing preprint {preprint._id} ({processed + 1}/{total})')

            if not dry_run:
                preprint.why_no_data = ''
                preprint.save()
                logger.info(f'Updated preprint {preprint._id}')
            else:
                logger.info(
                    f'Would update preprint {preprint._id} (dry run), {preprint.has_data_links=}, {preprint.why_no_data=}'
                )

            processed += 1
        except Exception as e:
            errors += 1
            logger.error(f'Error processing preprint {preprint._id}: {str(e)}')
            if through_command_constrain:
                command_obj.stdout.write(command_obj.style.ERROR(f'Error processing preprint {preprint._id}: {str(e)}'))
            continue

    logger.info(f'Completed processing {processed} preprints with {errors} errors')
    if through_command_constrain:
        command_obj.stdout.write(
            command_obj.style.SUCCESS(
                f'Completed processing {processed} preprints with {errors} errors'
            )
        )


class Command(BaseCommand):
    help = 'Fix preprints has_data_links and why_no_data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making changes',
        )
        parser.add_argument(
            '--guid',
            type=str,
            help='Version GUID to process (e.g. awgxb_v1, kupen_v4)',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        version_guid = options.get('guid')

        if dry_run:
            logger.info('Running in dry-run mode - no changes will be made')
            self.stdout.write('Running in dry-run mode - no changes will be made')

        process_wrong_why_not_data_preprints(
            version_guid=version_guid,
            dry_run=dry_run,
            executing_through_command=True,
            command_obj=self
        )
