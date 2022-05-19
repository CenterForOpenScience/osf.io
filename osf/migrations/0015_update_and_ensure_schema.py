import logging

from django.db import migrations

logger = logging.getLogger(__file__)
from osf.utils.migrations import ensure_schemas
from osf.utils.migrations import UpdateRegistrationSchemasAndSchemaBlocks


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0015_add_datacite_file_metadata_schema'),
    ]

    operations = [
        UpdateRegistrationSchemasAndSchemaBlocks(),
        migrations.RunPython(ensure_schemas),
    ]
