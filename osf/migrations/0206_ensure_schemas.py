from __future__ import unicode_literals

from django.db import migrations
from osf.utils.migrations import UpdateRegistrationSchemasAndSchemaBlocks

class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0205_auto_20200323_1850'),
    ]

    operations = [
        UpdateRegistrationSchemasAndSchemaBlocks(),
    ]
