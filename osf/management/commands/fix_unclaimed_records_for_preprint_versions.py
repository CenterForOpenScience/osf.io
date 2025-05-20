import logging

from django.core.management.base import BaseCommand
from django.apps import apps
from django.db.models import Q

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Update unclaimed records for preprint versions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            help='Run the command without saving changes',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        update_unclaimed_records_for_preprint_versions(dry_run=dry_run)

def safe_sort_key(x, delimiter):
    parts = x.split(delimiter)
    if len(parts) > 1:
        try:
            return int(parts[1])
        except (ValueError, TypeError):
            return 0
    return 0


def update_unclaimed_records_for_preprint_versions(dry_run=False):
    Preprint = apps.get_model('osf.Preprint')
    Guid = apps.get_model('osf.Guid')
    OSFUser = apps.get_model('osf.OSFUser')
    GuidVersionsThrough = apps.get_model('osf.GuidVersionsThrough')

    preprint_filters = (
        Q(preprintcontributor__user__is_registered=False) |
        Q(preprintcontributor__user__date_disabled__isnull=False)
    )

    mode = 'DRY RUN' if dry_run else 'UPDATING'
    logger.info(f'Starting {mode} for unclaimed records for preprint versions')

    preprints_count = Preprint.objects.filter(
        preprint_filters
    ).distinct('versioned_guids__guid').count()

    logger.info(f'Found {preprints_count} preprints with unregistered contributors')

    processed_count = 0
    skipped_count = 0
    updated_count = 0

    logger.info('-' * 50)
    logger.info(f'{mode} MODE')
    logger.info('-' * 50)

    for preprint in Preprint.objects.filter(
            preprint_filters
    ).prefetch_related('_contributors').distinct(
        'versioned_guids__guid'
    ):
        processed_count += 1
        try:
            guid, version = Guid.split_guid(preprint._id)
            logger.info(f'[{processed_count}/{preprints_count}] Processing preprint {preprint._id}')

            latest_version_through = GuidVersionsThrough.objects.filter(guid___id=guid).last()
            if not latest_version_through:
                logger.error(f'No version found for guid {guid}, skipping')
                skipped_count += 1
                continue

            latest_version_number = latest_version_through.version
            unregistered_contributors = preprint.contributor_set.filter(user__is_registered=False)
            logger.info(f'Found {unregistered_contributors.count()} unregistered contributors for preprint {preprint._id}')
            delimiter = Preprint.GUID_VERSION_DELIMITER
            for contributor in unregistered_contributors:
                try:
                    records_key_for_current_guid = [
                        key for key in contributor.user.unclaimed_records.keys() if guid in key and delimiter in key
                    ]
                    if records_key_for_current_guid:
                        records_key_for_current_guid.sort(
                            key=lambda x: safe_sort_key(x, delimiter),
                        )
                        record_info = contributor.user.unclaimed_records[records_key_for_current_guid[0]]
                        for current_version in range(1, int(latest_version_number) + 1):
                            preprint_id = f'{guid}{Preprint.GUID_VERSION_DELIMITER}{current_version}'
                            if preprint_id not in contributor.user.unclaimed_records.keys():
                                if not dry_run:
                                    try:
                                        preprint_obj = Preprint.load(preprint_id)
                                        referrer = OSFUser.load(record_info['referrer_id'])

                                        if not preprint_obj:
                                            logger.error(f'Could not load preprint {preprint_id}, skipping')
                                            continue

                                        if not referrer:
                                            logger.error(f'Could not load referrer {record_info["referrer_id"]}, skipping')
                                            continue

                                        logger.info(f'Adding unclaimed record for {preprint_id} for user {contributor.user._id}')
                                        contributor.user.unclaimed_records[preprint_id] = contributor.user.add_unclaimed_record(
                                            claim_origin=preprint_obj,
                                            referrer=referrer,
                                            given_name=record_info.get('name', None),
                                            email=record_info.get('email', None),
                                            skip_referrer_permissions=True
                                        )
                                        contributor.user.save()
                                        updated_count += 1
                                        logger.info(f'Successfully saved unclaimed record for {preprint_id}')
                                    except Exception as e:
                                        logger.error(f'Error adding unclaimed record for {preprint_id}: {str(e)}')
                                else:
                                    logger.info(f'[DRY RUN] Would add unclaimed record for {preprint_id} for user {contributor.user._id}')
                                    updated_count += 1
                    else:
                        try:
                            all_versions = [guid.referent for guid in GuidVersionsThrough.objects.filter(guid___id=guid)]
                            logger.info(f'Found {len(all_versions)} versions for preprint with guid {guid}')

                            for current_preprint in all_versions:
                                preprint_id = current_preprint._id
                                if preprint_id not in contributor.user.unclaimed_records.keys():
                                    if not dry_run:
                                        try:
                                            logger.info(f'Adding unclaimed record for {preprint_id} for user {contributor.user._id}')
                                            contributor.user.unclaimed_records[preprint_id] = contributor.user.add_unclaimed_record(
                                                claim_origin=current_preprint,
                                                referrer=current_preprint.creator,
                                                given_name=contributor.user.fullname,
                                                email=contributor.user.username,
                                                skip_referrer_permissions=True
                                            )
                                            contributor.user.save()
                                            updated_count += 1
                                            logger.info(f'Successfully saved unclaimed record for {preprint_id}')
                                        except Exception as e:
                                            logger.error(f'Error adding unclaimed record for {preprint_id}: {str(e)}')
                                    else:
                                        logger.info(f'[DRY RUN] Would add unclaimed record for {preprint_id} for user {contributor.user._id}')
                                        updated_count += 1
                        except Exception as e:
                            logger.error(f'Error processing versions for guid {guid}: {str(e)}')
                except Exception as e:
                    logger.error(f'Error processing contributor {contributor.id}: {str(e)}')

        except Exception as e:
            logger.error(f'Unexpected error processing preprint {preprint.id}: {str(e)}')
            skipped_count += 1

    if dry_run:
        logger.info(f'Processed: {processed_count}, Would update: {updated_count}, Skipped: {skipped_count}')
    else:
        logger.info(f'Processed: {processed_count}, Updated: {updated_count}, Skipped: {skipped_count}')
