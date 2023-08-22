"""Resend metadata for all (or some) public objects (registrations, preprints...) to SHARE/Trove
"""
import logging

from django.core.management.base import BaseCommand
from addons.osfstorage.models import OsfStorageFile
from osf.models import AbstractProvider, Registration, Preprint, Node, OSFUser
from api.share.utils import task__update_share

logger = logging.getLogger(__name__)


def recatalog(provided_model, providers, start_id, chunk_count, chunk_size):
    _chunk_start_id = start_id
    for _ in range(chunk_count):
        _last_id = recatalog_chunk(provided_model, providers, _chunk_start_id, chunk_size)
        if _last_id is None:
            logger.info('All done!')
            return
        _chunk_start_id = _last_id + 1


def recatalog_chunk(provided_model, providers, start_id, chunk_size):
    items = provided_model.objects.filter(
        id__gte=start_id,
    ).order_by('id')

    if providers is not None:
        items = items.filter(provider__in=providers)

    item_chunk = list(items[:chunk_size])
    last_id = None
    if item_chunk:
        first_id = item_chunk[0].id
        last_id = item_chunk[-1].id

        for item in item_chunk:
            guid = item.guids.values_list('_id', flat=True).first()
            if guid:
                task__update_share.apply_async(kwargs={'guid': guid, 'is_backfill': True})
            else:
                logger.debug('skipping item without guid: %s', item)

        logger.info(f'Queued metadata recataloguing for {len(item_chunk)} {provided_model.__name__}ses (ids in range [{first_id},{last_id}])')
    else:
        logger.info(f'Done recataloguing metadata for {provided_model.__name__}ses!')

    return last_id


class Command(BaseCommand):
    def add_arguments(self, parser):
        provider_group = parser.add_mutually_exclusive_group(required=True)
        provider_group.add_argument(
            '--providers',
            type=str,
            nargs='+',
            help='recatalog metadata for items from specific providers (by `_id`)',
        )
        provider_group.add_argument(
            '--all-providers',
            '-a',
            action='store_true',
            help='recatalog metadata for items from all providers',
        )

        type_group = parser.add_mutually_exclusive_group(required=True)
        type_group.add_argument(
            '--all-types',
            action='store_true',
            help='recatalog metadata for all catalogable types of items',
        )
        type_group.add_argument(
            '--preprints',
            action='store_true',
            help='recatalog metadata for preprints',
        )
        type_group.add_argument(
            '--registrations',
            action='store_true',
            help='recatalog metadata for registrations (and registration components)',
        )
        type_group.add_argument(
            '--projects',
            action='store_true',
            help='recatalog metadata for non-registration projects (and components)',
        )
        type_group.add_argument(
            '--files',
            action='store_true',
            help='recatalog metadata for files',
        )
        type_group.add_argument(
            '--users',
            action='store_true',
            help='recatalog metadata for users',
        )

        parser.add_argument(
            '--start-id',
            type=int,
            default=0,
            help='id to start from, if resuming a previous run (default 0)',
        )
        parser.add_argument(
            '--chunk-size',
            type=int,
            default=500,
            help='maximum number of items to query at one time',
        )
        parser.add_argument(
            '--chunk-count',
            type=int,
            default=int(9e9),
            help='maximum number of chunks (default all/enough/lots)',
        )

    def handle(self, *args, **options):
        pls_all_providers = options['all_providers']
        pls_all_types = options['all_types']
        pls_recatalog_preprints = options['preprints']
        pls_recatalog_registrations = options['registrations']
        pls_recatalog_projects = options['projects']
        pls_recatalog_files = options['files']
        pls_recatalog_users = options['users']
        start_id = options['start_id']
        chunk_size = options['chunk_size']
        chunk_count = options['chunk_count']

        if pls_all_providers:
            providers = None  # `None` means "don't filter by provider"
        else:
            provider_ids = options['providers']
            providers = AbstractProvider.objects.filter(_id__in=provider_ids)

        if pls_all_types:
            assert not start_id, 'choose a specific type to resume with --start-id'
            provided_models = [Preprint, Registration, Node, OSFUser, OsfStorageFile]
        else:
            if pls_recatalog_preprints:
                provided_models = [Preprint]
            if pls_recatalog_registrations:
                provided_models = [Registration]
            if pls_recatalog_projects:
                provided_models = [Node]
            if pls_recatalog_files:
                provided_models = [OsfStorageFile]
            if pls_recatalog_users:
                provided_models = [OSFUser]

        for provided_model in provided_models:
            recatalog(provided_model, providers, start_id, chunk_count, chunk_size)
