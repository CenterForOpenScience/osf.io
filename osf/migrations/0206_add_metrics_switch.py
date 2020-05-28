# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2019-07-23 14:26
from __future__ import unicode_literals
from django.db import migrations

from osf import features
from osf.utils.migrations import AddWaffleSwitches

class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0205_auto_20200323_1850'),
    ]

    operations = [
        AddWaffleSwitches([features.ENABLE_RAW_METRICS], active=False),
    ]
