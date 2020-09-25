import logging
import osf.utils.migrations as migrations
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

def update_registration_schemas():
    """Update the regitration schemas to match the locally defined schemas."""
    logger.debug('Updating Registration Schemas')
    migrations.ensure_schemas()
    logger.debug('Updating Registration Schema Blocks')
    migrations.map_schemas_to_schemablocks()

class Command(BaseCommand):

    def handle(self, *args, **options):
        update_registration_schemas()
