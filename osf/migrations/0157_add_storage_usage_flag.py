# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import migrations

from osf import features
from osf.utils.migrations import AddWaffleFlags


class Migration(migrations.Migration):
    dependencies = [
        ('osf', '0156_create_cache_table'),
    ]

    operations = [
        AddWaffleFlags([features.STORAGE_USAGE]),
    ]
