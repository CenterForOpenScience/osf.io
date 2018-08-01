

import logging

from django.db import migrations
from osf.utils.migrations import ensure_schemas, remove_schemas


logger = logging.getLogger(__file__)


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0105_merge_20180525_1529'),
    ]

    operations = [
        migrations.RunPython(ensure_schemas, remove_schemas),
    ]
