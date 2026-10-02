import logging
import datetime

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from framework.auth.core import Auth
from osf.models import Preprint, GuidVersionsThrough, OSFUser
from website.files.utils import copy_files

logger = logging.getLogger(__name__)


def find_broken_recovered_preprints():
    preprint_ct = ContentType.objects.get_for_model(Preprint)

    broken_qs = Preprint.objects.filter(
        primary_file__isnull=True,
        deleted__isnull=True,
    ).order_by('id')

    for broken in broken_qs.iterator():
        gvt = GuidVersionsThrough.objects.filter(
            content_type=preprint_ct, object_id=broken.id,
        ).first()
        if not gvt:
            continue

        earlier_versions = GuidVersionsThrough.objects.filter(
            guid=gvt.guid, content_type=preprint_ct, version__lt=gvt.version,
        ).order_by('-version')

        for earlier in earlier_versions:
            donor = Preprint.objects.filter(id=earlier.object_id).first()
            if donor and donor.deleted and donor.primary_file_id:
                yield broken, donor
                break


def repair_recovered_preprint_files(dry_run=False, user_id=None):
    pairs = list(find_broken_recovered_preprints())
    published_pairs = [(b, d) for b, d in pairs if b.is_published]
    unpublished_pairs = [(b, d) for b, d in pairs if not b.is_published]

    logger.info(
        f'Found {len(pairs)} broken recovered preprint(s): '
        f'{len(published_pairs)} published (will repair), '
        f'{len(unpublished_pairs)} unpublished (flagged only - still mid-recovery, '
        'an admin may be deliberately holding off on a file; not auto-repaired)',
    )
    for broken, donor in unpublished_pairs:
        logger.info(
            f'{broken._id}: UNPUBLISHED, missing primary_file, donor is soft-deleted '
            f'version {donor._id} with primary_file {donor.primary_file._id} - review manually',
        )

    if not published_pairs:
        return

    acting_user = OSFUser.load(user_id) if user_id else None

    for broken, donor in published_pairs:
        logger.info(
            f'{broken._id}: missing primary_file, donor is soft-deleted '
            f'version {donor._id} with primary_file {donor.primary_file._id}',
        )
        if dry_run:
            continue

        auth = Auth(acting_user or donor.creator)
        latest_version = donor.primary_file.versions.order_by('-created').first()
        copied = copy_files(donor.primary_file, target_node=broken, identifier=latest_version.identifier)
        broken.set_primary_file(copied, auth=auth, save=True)
        logger.info(f'{broken._id}: attached primary_file {copied._id} (copied from {donor._id})')


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry_run',
            action='store_true',
            default=False,
            help='List affected preprints without writing changes',
        )
        parser.add_argument(
            '--user_id',
            type=str,
            default=None,
            help='OSFUser _id to record as the acting user for the file-attach log entry '
                 '(defaults to the donor version\'s creator)',
        )

    def handle(self, *args, **options):
        script_start_time = datetime.datetime.now()
        logger.info(f'Script started time: {script_start_time}')

        dry_run = options['dry_run']
        if dry_run:
            logger.info('DRY RUN. Data will not be saved.')

        repair_recovered_preprint_files(dry_run=dry_run, user_id=options['user_id'])

        script_finish_time = datetime.datetime.now()
        logger.info(f'Script finished time: {script_finish_time}')
        logger.info(f'Run time {script_finish_time - script_start_time}')
