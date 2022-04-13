import logging

from django.db import migrations

logger = logging.getLogger(__file__)
from osf.models import RegistrationSchema
from website.project.metadata.schemas import ensure_schema_structure, from_json


def add_schema(apps, schema_editor):
    schema = ensure_schema_structure(from_json('secondary-data.json'))

    RegistrationSchema.objects.filter(name=schema['name']).update(visible=False, active=True)


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0226_auto_20210224_1610'),
    ]

    operations = [
    ]
