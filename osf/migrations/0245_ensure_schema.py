# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from osf.utils.migrations import UpdateRegistrationSchemasAndSchemaBlocks


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0244_merge_20250328'),
    ]

    operations = [
        UpdateRegistrationSchemasAndSchemaBlocks(),
    ]
