# -*- coding: utf-8 -*-
# This is an auto-migration and not a management command because:
#   1. The next script would fail if duplicate records existed
#   2. This should only need to be run once
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0020_auto_20170426_0920'),
    ]

    operations = [
    ]
