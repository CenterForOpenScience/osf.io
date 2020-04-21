from django.core.management.base import BaseCommand

from osf.models import Preprint, PreprintProvider


"""
A management command to migrate preperints from one provider to another.

i.e. docker-compose run --rm web python3 manage.py migrate_preprint_providers --source_provider lawarxiv --destination_provider osf
"""


def migrate_preprint_providers(source_provider_guid, destination_provider_guid):
    source_provider = PreprintProvider.load(source_provider_guid)
    destination_provider = PreprintProvider.load(destination_provider_guid)
    migration_count = 0

    for preprint in Preprint.objects.filter(provider=source_provider):
        preprint.provider = destination_provider
        preprint.save()
        migration_count += 1

    return migration_count


class Command(BaseCommand):
    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--source_provider',
            help='The preprint provider to migrate from',
        )
        parser.add_argument(
            '--destination_provider',
            help='The preprint provider to migrate to',
        )

    def handle(self, *args, **options):
        source_provider_guid = options.get('source_provider', False)
        destination_provider_guid = options.get('destination_provider', False)

        if source_provider_guid and destination_provider_guid:
            migration_count = migrate_preprint_providers(source_provider_guid, destination_provider_guid)

        print(f'{migration_count} preprints were migrated from {source_provider_guid} to {destination_provider_guid}')
