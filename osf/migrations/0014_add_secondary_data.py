import logging

from django.db import migrations

logger = logging.getLogger(__file__)
from osf.models import RegistrationSchema
from osf.utils.migrations import ensure_schemas
from website.project.metadata.schemas import ensure_schema_structure, from_json
from osf.utils.migrations import UpdateRegistrationSchemasAndSchemaBlocks


def add_schema(apps, schema_editor):
    schema = ensure_schema_structure(from_json('secondary-data.json'))

    RegistrationSchema.objects.filter(name=schema['name']).update(visible=False, active=True)


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0013_add_schemas'),
    ]

    operations = [
        UpdateRegistrationSchemasAndSchemaBlocks(),
        migrations.RunPython(add_schema, ensure_schemas),
    ]
