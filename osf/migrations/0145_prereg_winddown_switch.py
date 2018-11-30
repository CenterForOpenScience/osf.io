# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

from osf import features
from osf.utils.migrations import AddWaffleSwitch, UpdateRegistrationSchemas


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0144_enable_inactive_schemas_switch'),
    ]

    operations = [
        AddWaffleSwitch(features.OSF_PREREGISTRATION, active=False),
        UpdateRegistrationSchemas(),
    ]
