# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def ensure_registration_mappings(*args):
    from api.base import settings
    from addons.weko.apps import NAME
    from addons.weko.utils import ensure_registration_metadata_mapping
    from addons.weko.mappings import REGISTRATION_METADATA_MAPPINGS
    if NAME not in settings.INSTALLED_APPS:
        return
    for schema_name, mappings in REGISTRATION_METADATA_MAPPINGS:
        ensure_registration_metadata_mapping(schema_name, mappings)

class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0236_add_columns_to_registration_schema_block'),
    ]

    operations = [
        migrations.RunPython(ensure_registration_mappings, ensure_registration_mappings),
    ]
