"""
This script is destructive and should be used with caution.
Before use, a new provider must already be created with correct subjects and assets.

A change to the nginx config, redirecting "/preprints/<src_id>/*" to "/preprints/<dst_id>/*"
must go out when this is ran.
"""
import logging

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count
from tqdm import tqdm

from scripts import utils as script_utils
# There is no such file as reindex_preprint_provider, so it was replaced with reindex_provider
from osf.management.commands.reindex_provider import reindex_provider
from osf.models import PreprintProvider
from osf.utils.migrations import disable_auto_now_fields

logger = logging.getLogger(__name__)


def rebrand_provider(src_id, dst_id):
    assert src_id != 'osf', 'Cannot rebrand OSF Preprints'
    src_prov = PreprintProvider.load(src_id)
    dst_prov = PreprintProvider.load(dst_id)
    assert src_prov, f'Unable to find provider {src_id}'
    assert dst_prov, f'Unable to find provider {dst_id}'
    assert set(src_prov.subjects.values_list('text', flat=True)) == set(dst_prov.subjects.values_list('text', flat=True)), 'Provider subjects do not match'
    assert set(src_prov.licenses_acceptable.values_list('id', flat=True)) == set(dst_prov.licenses_acceptable.values_list('id', flat=True)), 'Provider licenses do not match'
    assert set(src_prov.notification_subscriptions.values_list('event_name', flat=True)) == set(dst_prov.notification_subscriptions.values_list('event_name', flat=True)), 'Provider subscription events do not match'
    assert dst_prov.asset_files.filter(name='square_color_no_transparent').exists(), f'Invalid assets on {dst_id}'
    assert dst_prov.access_token, 'Destination Provider must have a SHARE access token'

    logger.info(f'Updating {src_id}\'s preprints to provider {dst_id}')
    src_prov.preprints.update(provider_id=dst_prov.id)

    logger.info(f'Updating preprint subjects with {dst_id} equivalent subjects')
    target_preprints = dst_prov.preprints.all()
    pbar = tqdm(total=target_preprints.count() or 1)
    for i, pp in enumerate(target_preprints, 1):
        pbar.update()
        # M2M .set does not require .save
        pp.subjects.set(dst_prov.subjects.filter(text__in=list(pp.subjects.values_list('text', flat=True))))
    pbar.close()

    logger.info(f'Updating {dst_id} moderators')
    dst_prov.get_group('admin').user_set.set(src_prov.get_group('admin').user_set.all())
    dst_prov.get_group('moderator').user_set.set(src_prov.get_group('moderator').user_set.all())

    logger.info(f'Updating {dst_id} notification subscriptions')
    for src_sub in src_prov.notification_subscriptions.all():
        dst_sub = dst_prov.notification_subscriptions.get(event_name=src_sub.event_name)
        dst_sub.email_transactional.set(src_sub.email_transactional.all())
        dst_sub.email_digest.set(src_sub.email_digest.all())
        dst_sub.none.set(src_sub.none.all())

    logger.info(f'Updating {dst_id} notification digests')
    src_prov.notificationdigest_set.update(provider_id=dst_prov.id)


def delete_old_provider(src_id):
    src_prov = PreprintProvider.load(src_id)
    assert src_prov.preprints.count() == 0, f'Provider {src_id} still has preprints'
    assert src_prov.notificationdigest_set.count() == 0, 'Provider {} still has queued digest emails'
    assert src_prov.subjects.annotate(pc=Count('preprints')).filter(pc__gt=0).count() == 0, f'Provider {src_id} still has used subjects'

    # I don't trust CASCADE deletes to be set up correctly
    logger.warning('Deleting Assets: {}'.format(src_prov.asset_files.annotate(pc=Count('providers')).filter(pc=1).delete()))
    logger.warning(f'Deleting Groups: {src_prov.group_objects.delete()}')
    logger.warning(f'Deleting Subjects: {src_prov.subjects.all().delete()}')
    logger.warning(f'Deleting Subscriptions: {src_prov.notification_subscriptions.all().delete()}')
    logger.warning(f'Deleting Provider: {src_prov.delete()}')


def reindex_share(dst_id, dry_run):
    dst_prov = PreprintProvider.load(dst_id)
    if dry_run:
        logger.info(f'Would send {dst_prov.preprints.count()} preprints to SHARE...')
    else:
        reindex_provider(dst_prov)


class Command(BaseCommand):
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='Pretend to rebrand, neither commit changes nor send updates to SHARE',
        )
        parser.add_argument(
            '--source',
            type=str,
            required=True,
            dest='source',
            help='Old provider _id to migrate from and delete',
        )
        parser.add_argument(
            '--dest',
            type=str,
            required=True,
            dest='dest',
            help='New provider _id to migrate into',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        src = options.get('source')
        dest = options.get('dest')
        if not dry_run:
            script_utils.add_file_logger(logger, __file__)
        with transaction.atomic():
            with disable_auto_now_fields():
                rebrand_provider(src, dest)
                delete_old_provider(src)
                reindex_share(dest, dry_run)
            if dry_run:
                raise RuntimeError('Dry Run -- Transaction rolled back')
