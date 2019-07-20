# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import migrations

from osf import features
from osf.utils.migrations import AddWaffleFlags


class Migration(migrations.Migration):
    dependencies = [
        ('osf', '0166_merge_20190429_1632'),
    ]

    operations = [
        AddWaffleFlags([features.OSF_GROUPS], on_for_everyone=False),
    ]
