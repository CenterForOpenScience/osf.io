from __future__ import unicode_literals

import logging

from django.db import migrations
from osf.utils.migrations import ensure_schemas, remove_schemas


logger = logging.getLogger(__file__)

def update_schemas(state, schema):
    remove_schemas()
    ensure_schemas()


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0141_merge_20181023_1526'),
    ]

    operations = [
        # To reverse this migrations simply revert changes to the schema and re-run
        migrations.RunPython(update_schemas, update_schemas),
    ]
