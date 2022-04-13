from __future__ import unicode_literals

import logging

from django.db import migrations


logger = logging.getLogger(__file__)


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0105_merge_20180525_1529'),
    ]

    operations = [
    ]
