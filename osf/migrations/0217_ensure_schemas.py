# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from osf.utils.migrations import ensure_schemas


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0216_merge_20211009_0007'),
    ]

    operations = [
        # To reverse this migrations simply revert changes to the schema and re-run
        migrations.RunPython(ensure_schemas, ensure_schemas),
    ]
