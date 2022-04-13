from __future__ import unicode_literals

import logging

from django.db import migrations


logger = logging.getLogger(__file__)


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0077_add_maintenance_permissions'),
    ]

    operations = [
    ]
