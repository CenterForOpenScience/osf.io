# -*- coding: utf-8 -*-
import logging

from django.core.management.base import BaseCommand
from osf.models import RegistrationSchema
from website.project.metadata.schemas import ensure_schema_structure, from_json

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Add egap-registration schema to the db.
    For now, doing this outside of a migration so it can be individually added to
    a staging environment for preview.
    """

    def handle(self, *args, **options):
        egap_registration_schema = ensure_schema_structure(from_json('egap-registration-3.json'))
        schema_obj, created = RegistrationSchema.objects.update_or_create(
            name=egap_registration_schema['name'],
            schema_version=egap_registration_schema.get('version', 1),
            defaults={
                'schema': egap_registration_schema,
            }
        )

        if created:
            logger.info('Added schema {} to the database'.format(egap_registration_schema['name']))
        else:
            logger.info('updated existing schema {}'.format(egap_registration_schema['name']))
