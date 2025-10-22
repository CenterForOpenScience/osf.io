# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from osf.utils.migrations import UpdateRegistrationSchemasAndSchemaBlocks


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0254_ensure_schema_mappings'),
    ]

    operations = [
        UpdateRegistrationSchemasAndSchemaBlocks(),
    ]
