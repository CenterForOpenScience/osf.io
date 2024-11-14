"""Resend metadata for all (or some) public objects (registrations, preprints...) to SHARE/Trove
"""
import logging

from django.core.management.base import BaseCommand
from addons.osfstorage.models import OsfStorageFile
from osf.models import AbstractProvider, Registration, Preprint, Node, OSFUser
from api.share.utils import task__update_share
from website.settings import CeleryConfig


logger = logging.getLogger(__name__)


def recatalog(queryset, start_id, chunk_count, chunk_size):
    _chunk_start_id = start_id
    for _ in range(chunk_count):
        _last_id = recatalog_chunk(queryset, _chunk_start_id, chunk_size)
        if _last_id is None:
            logger.info('All done!')
            return
        _chunk_start_id = _last_id + 1


def recatalog_chunk(queryset, start_id, chunk_size):
    item_chunk = list(
        queryset
        .filter(id__gte=start_id)
        .order_by('id')
        [:chunk_size]
    )
    last_id = None
    if item_chunk:
        first_id = item_chunk[0].id
        last_id = item_chunk[-1].id

        for item in item_chunk:
            guid = item.guids.values_list('_id', flat=True).first()
            if guid:
                task__update_share.apply_async(
                    kwargs={'guid': guid, 'is_backfill': True},
                    queue=CeleryConfig.task_low_queue,  # "low priority" queue
                )
            else:
                logger.debug('skipping item without guid: %s', item)

        logger.info(f'Queued metadata recataloguing for {len(item_chunk)} {queryset.model.__name__}ses (ids in range [{first_id},{last_id}])')
    else:
        logger.info(f'Done recataloguing metadata for {queryset.model.__name__}ses!')

    return last_id


def _recatalog_all(queryset, chunk_size):
    recatalog(queryset, start_id=0, chunk_count=int(9e9), chunk_size=chunk_size)


class Command(BaseCommand):
    def add_arguments(self, parser):
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

        provider_group = parser.add_mutually_exclusive_group()
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
            help='recatalog metadata for items from all providers (default if no --providers given)',
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
        parser.add_argument(
            '--also-decatalog',
            action='store_true',
            help='also remove private and deleted items from the catalog',
        )

    def handle(self, *args, **options):
        pls_all_types = options['all_types']
        pls_recatalog_preprints = options['preprints']
        pls_recatalog_registrations = options['registrations']
        pls_recatalog_projects = options['projects']
        pls_recatalog_files = options['files']
        pls_recatalog_users = options['users']
        provider_ids = options.get('providers')
        start_id = options['start_id']
        chunk_size = options['chunk_size']
        chunk_count = options['chunk_count']
        also_decatalog = options['also_decatalog']

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
            _queryset = provided_model.objects
            if provider_ids is not None:
                _queryset = _queryset.filter(
                    provider__in=AbstractProvider.objects.filter(_id__in=provider_ids),
                )
            if not also_decatalog:
                if provided_model is OsfStorageFile:
                    _queryset = _queryset.filter(deleted__isnull=True)
                elif provided_model is OSFUser:
                    _queryset = _queryset.filter(
                        deleted__isnull=True,
                        is_active=True,
                    ).exclude(allow_indexing=False)
                elif provided_model is Preprint:
                    _queryset = _queryset.filter(is_public=True, is_published=True, deleted__isnull=True)
                else:
                    _queryset = _queryset.filter(is_public=True, deleted__isnull=True)
            recatalog(_queryset, start_id, chunk_count, chunk_size)
