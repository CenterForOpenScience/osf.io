from __future__ import unicode_literals

import logging

from django.db import migrations
from osf.utils.migrations import ensure_schemas, remove_schemas


logger = logging.getLogger(__file__)


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0095_reset_osf_abstractprovider_licenses_acceptable_id_seq'),
    ]

    operations = [
        migrations.RunPython(ensure_schemas, remove_schemas),
    ]
