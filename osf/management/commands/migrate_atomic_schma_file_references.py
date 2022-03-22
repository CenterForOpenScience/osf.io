from django.core.management.base import BaseCommand
from django.db import transaction

from osf.models import RegistrationSchema
from website.archiver.utils import migrate_file_metadata


@transaction.atomic
def migrate_atomic_schema_file_references(dry=False):
    for schema in RegistrationSchema.objects.all():
        if not schema.schema.get('atomicSchema', False):
            continue
        for registration in schema.registration_set.all():
            migrate_file_metadata(registration)

    if dry:
        raise RuntimeError('Dry run, rolling back transaction')


class Command(BaseCommand):
    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='Dry run',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run')
        migrate_atomic_schema_file_references(dry_run=dry_run)
