# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from osf.utils.migrations import UpdateRegistrationSchemasAndSchemaBlocks


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
        ('addons_weko', '0005_registrationmetadatamapping'),
        ('osf', '0229_merge_20230617_1021'),
    ]

    operations = [
        UpdateRegistrationSchemasAndSchemaBlocks(),
        migrations.RunPython(ensure_registration_mappings, ensure_registration_mappings),
    ]
