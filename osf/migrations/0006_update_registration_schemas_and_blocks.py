from __future__ import unicode_literals

from django.db import migrations
from osf.utils.migrations import UpdateRegistrationSchemasAndSchemaBlocks

class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0005_ensure_subjects_and_providers'),
    ]

    operations = [
        UpdateRegistrationSchemasAndSchemaBlocks(),
    ]
