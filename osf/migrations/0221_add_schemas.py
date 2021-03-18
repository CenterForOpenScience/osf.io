import logging

from django.db import migrations

logger = logging.getLogger(__file__)
from osf.models import RegistrationSchema
from osf.utils.migrations import ensure_schemas
from website.project.metadata.schemas import ensure_schema_structure, from_json
from osf.utils.migrations import UpdateRegistrationSchemasAndSchemaBlocks


def add_invisible_schemas(apps, schema_editor):
    schemas = [
        ensure_schema_structure(from_json('asist-hypothesis-capability-registration.json')),
        ensure_schema_structure(from_json('asist-results-registration.json')),
        ensure_schema_structure(from_json('real-world-evidence.json')),
    ]

    schema_names = [schema['name'] for schema in schemas]

    RegistrationSchema.objects.filter(name__in=schema_names).update(visible=False, active=True)


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0219_auto_20201020_1836'),
    ]

    operations = [
        UpdateRegistrationSchemasAndSchemaBlocks(),
        migrations.RunPython(add_invisible_schemas, ensure_schemas),
    ]
