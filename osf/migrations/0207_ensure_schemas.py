from __future__ import unicode_literals

from django.db import migrations
from osf.utils.migrations import UpdateRegistrationSchemasAndSchemaBlocks

class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0206_auto_20200528_1319'),
    ]

    operations = [
        UpdateRegistrationSchemasAndSchemaBlocks(),
    ]
