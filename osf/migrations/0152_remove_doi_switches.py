# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

from osf.utils.migrations import DeleteWaffleSwitches


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0151_auto_20181215_1911'),
    ]

    operations = [
        DeleteWaffleSwitches(['disable_datacite_dois', 'ezid_switch']),
    ]
