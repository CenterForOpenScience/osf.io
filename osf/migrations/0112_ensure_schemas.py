from __future__ import unicode_literals

import logging

from django.db import migrations

logger = logging.getLogger(__file__)


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0111_auto_20180605_1240'),
    ]

    operations = []
