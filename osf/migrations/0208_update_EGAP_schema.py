from __future__ import unicode_literals

from django.db import migrations
from osf.utils.migrations import UpdateRegistrationSchemasAndSchemaBlocks

def noop(*args, **kwargs):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0207_update_schemas2'),
    ]

    operations = [
        UpdateRegistrationSchemasAndSchemaBlocks(),
    ]
