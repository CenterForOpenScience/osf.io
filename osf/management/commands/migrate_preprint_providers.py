import logging

from django.core.management.base import BaseCommand
from django.db import transaction

from osf.models import Preprint, PreprintProvider


"""
A management command to migrate preperints from one provider to another.

i.e. docker-compose run --rm web python3 manage.py migrate_preprint_providers --source_provider lawarxiv --destination_provider osf
"""


logger = logging.getLogger(__name__)


def migrate_preprint_providers(source_provider_guid, destination_provider_guid, delete_source_provider=False):
    source_provider = PreprintProvider.load(source_provider_guid)
    destination_provider = PreprintProvider.load(destination_provider_guid)
    migration_count = 0

    for preprint in Preprint.objects.filter(provider=source_provider):
        preprint.map_subjects_between_providers(source_provider, destination_provider)
        preprint.provider = destination_provider
        preprint.save()
        logger.info(f'{preprint._id} has been migrated from {source_provider_guid} to {destination_provider_guid}.')
        migration_count += 1

    if delete_source_provider:
        source_provider.delete()
        logger.info(f'{source_provider_guid} has been deleted.')

    return migration_count


class Command(BaseCommand):
    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--dry_run',
            type=bool,
            default=False,
            help='Iterate and print out preprints that would be migrated without making any changes',
        )
        parser.add_argument(
            '--source_provider',
            help='Guid of the preprint provider to migrate from',
            required=True,
        )
        parser.add_argument(
            '--destination_provider',
            help='Guid of the preprint provider to migrate to',
            required=True,
        )
        parser.add_argument(
            '--delete_source_provider',
            type=bool,
            default=False,
            help='Delete the source provider after migrating all preprints'
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run')
        source_provider_guid = options.get('source_provider')
        destination_provider_guid = options.get('destination_provider')
        delete_source_provider = options.get('delete_source_provider')

        with transaction.atomic():
            migration_count = migrate_preprint_providers(
                source_provider_guid,
                destination_provider_guid,
                delete_source_provider=delete_source_provider)
            logger.info(f'{migration_count} preprints were migrated from {source_provider_guid} to {destination_provider_guid}.')
            if dry_run:
                raise RuntimeError('Dry run, transaction rolled back')
