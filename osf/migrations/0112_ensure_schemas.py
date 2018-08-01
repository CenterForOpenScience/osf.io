

import logging

from django.db import migrations
from osf.utils.migrations import ensure_schemas, remove_schemas


logger = logging.getLogger(__file__)
from osf.utils.migrations import ensure_schemas, remove_schemas


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0111_auto_20180605_1240'),
    ]

    operations = [
        migrations.RunPython(ensure_schemas, remove_schemas),
    ]
