# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

from osf.utils.migrations import AddWaffleSwitches


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0148_merge_20181213_2253'),
    ]

    operations = [
        AddWaffleSwitches(['disable_datacite_dois'], active=False),
    ]
