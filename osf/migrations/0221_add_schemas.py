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

    schema_names = [schema['name'] for schema in schemas]

    RegistrationSchema.objects.filter(name__in=schema_names).update(visible=False)


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0218_auto_20200929_1850'),
    ]

    operations = [
        migrations.RunPython(add_invisible_schemas, ensure_schemas),
    ]
