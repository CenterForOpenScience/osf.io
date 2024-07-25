import logging

from django.core.management.base import BaseCommand
from django.db import transaction
from osf.utils import migrations

logger = logging.getLogger(__name__)

@transaction.atomic
def update_registration_schemas(dry_run=False):
    """Update the regitration schemas to match the locally defined schemas."""
    logger.debug('Updating Registration Schemas')
    migrations.ensure_schemas()
    logger.debug('Updating Registration Schema Blocks')
    migrations.map_schemas_to_schemablocks()
    if dry_run:
        raise RuntimeError('Dry run, transaction rolled back')


class Command(BaseCommand):

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='Dry run',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run')
        update_registration_schemas(dry_run=dry_run)
