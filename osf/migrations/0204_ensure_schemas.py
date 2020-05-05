from __future__ import unicode_literals

from django.db import migrations
from osf.utils.migrations import UpdateRegistrationSchemasAndSchemaBlocks

class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0203_auto_20200312_1435'),
    ]

    operations = [
        UpdateRegistrationSchemasAndSchemaBlocks(),
    ]
