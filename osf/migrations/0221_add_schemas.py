import logging

from django.db import migrations

logger = logging.getLogger(__file__)
from osf.models import RegistrationSchema
from osf.utils.migrations import ensure_schemas
from website.project.metadata.schemas import ensure_schema_structure, from_json


def add_invisible_schemas(apps, schema_editor):
    schemas = [
        ensure_schema_structure(from_json('asist-hypothesis-capability-registration.json')),
        ensure_schema_structure(from_json('asist-results-registration.json')),
        ensure_schema_structure(from_json('real-world-evidence.json')),
        ensure_schema_structure(from_json('qualitative-research.json'))
    ]

    for schema in schemas:
        schema_obj, created = RegistrationSchema.objects.update_or_create(
            name=schema['name'],
            visible=False,
            schema_version=schema.get('version', 1),
            defaults={
                'schema': schema,
            }
        )
        schema_obj.save()


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0220_add_registration_provider_subscription'),
    ]

    operations = [
        migrations.RunPython(add_invisible_schemas, ensure_schemas),
    ]
