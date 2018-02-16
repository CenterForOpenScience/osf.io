from __future__ import unicode_literals

import logging

from django.db import migrations
from osf.utils.migrations import ensure_schemas, remove_schemas


logger = logging.getLogger(__file__)


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0079_merge_20180207_1545'),
    ]

    operations = [
        migrations.RunPython(ensure_schemas, remove_schemas),
    ]
