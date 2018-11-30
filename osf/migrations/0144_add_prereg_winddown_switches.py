# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

from osf import features
from osf.utils.migrations import AddWaffleSwitch


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0143_merge_20181115_1458'),
    ]

    operations = [
        AddWaffleSwitch(features.ENABLE_INACTIVE_SCHEMAS, active=False),
        AddWaffleSwitch(features.OSF_PREREGISTRATION, active=False)
    ]
