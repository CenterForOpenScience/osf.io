import logging

from django.core.management.base import BaseCommand

from osf.models import Registration
from osf.models.schema_responses import SchemaResponses

logger = logging.getLogger(__name__)

def migrate_schema_responses():
    """
    A management command to transfer schema response JSON into SchemaResponse objects
    """
    for reg in Registration.objects.filter(registration_responses__isnull=False):
        SchemaResponses.objects.create(
            created=reg.registered_date,
            schema=reg.registered_schema.first(),  # currently there is only one schema per registration
            node=reg,
            _responses=reg.registration_responses
        )

class Command(BaseCommand):

    def handle(self, *args, **options):
        migrate_schema_responses(*args, **options)
