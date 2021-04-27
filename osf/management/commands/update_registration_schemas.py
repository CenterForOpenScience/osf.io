import logging
from django.core.management.base import BaseCommand
from osf.utils.migrations import ensure_schemas, map_schemas_to_schemablocks

logger = logging.getLogger(__name__)

def update_registration_schemas():
    """Update the regitration schemas to match the locally defined schemas."""
    logger.debug('Updating Registration Schemas')
    ensure_schemas()
    logger.debug('Updating Registration Schema Blocks')
    map_schemas_to_schemablocks()

class Command(BaseCommand):

    def handle(self, *args, **options):
        update_registration_schemas()
