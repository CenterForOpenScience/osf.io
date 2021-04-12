"""Resend metadata for all (or some) public objects (registrations, preprints...) to SHARE/Trove
"""
import logging

from django.core.management.base import BaseCommand
from osf.models import AbstractProvider, Registration, Preprint, Node
from api.share.utils import update_share

logger = logging.getLogger(__name__)


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
            update_share(item)

        logger.info(f'Recatalogued metadata for {len(item_chunk)} {provided_model.__name__}ses (ids in range [{first_id},{last_id}])')
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
        pls_recatalog_preprints = options['preprints']
        pls_recatalog_registrations = options['registrations']
        pls_recatalog_projects = options['projects']
        start_id = options['start_id']
        chunk_size = options['chunk_size']
        chunk_count = options['chunk_count']

        if pls_all_providers:
            providers = None  # `None` means "don't filter by provider"
        else:
            provider_ids = options['providers']
            providers = AbstractProvider.objects.filter(_id__in=provider_ids)

        provided_model = None
        if pls_recatalog_preprints:
            provided_model = Preprint
        if pls_recatalog_registrations:
            provided_model = Registration
        if pls_recatalog_projects:
            provided_model = Node

        for _ in range(chunk_count):
            last_id = recatalog_chunk(provided_model, providers, start_id, chunk_size)
            if last_id is None:
                logger.info('All done!')
                return
            start_id = last_id + 1
