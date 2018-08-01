# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from osf.models import Registration, RegistrationSchema

PREREG_SCHEMA_NAMES = [
    'Prereg Challenge',
    'AsPredicted Preregistration',
    'OSF-Standard Pre-Data Collection Registration',
    'Replication Recipe (Brandt et al., 2013): Pre-Registration',
    "Pre-Registration in Social Psychology (van 't Veer & Giner-Sorolla, 2016): Pre-Registration",
    'Election Research Preacceptance Competition',
]

class Command(BaseCommand):
    """Get a count of preregistrations, grouped by schema."""

    def handle(self, *args, **options):
        total = 0
        for schema_name in PREREG_SCHEMA_NAMES:
            schemas = RegistrationSchema.objects.filter(name=schema_name).only('id', 'schema_version')
            for schema in schemas:
                registrations = Registration.objects.filter(registered_schema=schema).get_roots()
                count = registrations.count()
                print(('{} (Version {}): {}'.format(schema_name, schema.schema_version, count)))
                total += count
        print(('Total: {}'.format(total)))
