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


def _recatalog_datacite_custom_types(chunk_size):
    logger.info('recataloguing items with datacite custom type...')
    # all preprints
    _recatalog_all(Preprint.objects, chunk_size)
    # objects with custom resource_type_general
    for _model in {Registration, Node, OsfStorageFile}:
        _queryset = (
            _model.objects
            .exclude(guids__metadata_record__isnull=True)
            .exclude(guids__metadata_record__resource_type_general='')
        )
        _recatalog_all(_queryset, chunk_size)
    logger.info('done recataloguing items with datacite custom type!')


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
        type_group.add_argument(
            '--datacite-custom-types',
            action='store_true',
            help='''recatalog metadata for items with a specific datacite type,
            including all preprints and items with custom resource_type_general
            (may be slow for lack of database indexes)
            ''',
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
        datacite_custom_types = options['datacite_custom_types']

        if datacite_custom_types:  # temporary arg for datacite 4.5 migration
            assert not start_id, 'oh no, cannot resume with `--datacite-custom-types`'
            assert not provider_ids, 'oh no, cannot filter providers with `--datacite-custom-types`'
            _recatalog_datacite_custom_types(chunk_size)
            return  # end

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
            recatalog(_queryset, start_id, chunk_count, chunk_size)
