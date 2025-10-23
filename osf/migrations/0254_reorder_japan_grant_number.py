# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

from osf.utils.migrations import UpdateRegistrationSchemasAndSchemaBlocks


def ensure_registration_mappings(*args):
    from api.base import settings
    from addons.weko.apps import NAME
    from addons.weko.mappings import REGISTRATION_METADATA_MAPPINGS
    from addons.weko.utils import ensure_registration_metadata_mapping

    if NAME not in settings.INSTALLED_APPS:
        return

    for schema_name, mappings in REGISTRATION_METADATA_MAPPINGS:
        ensure_registration_metadata_mapping(schema_name, mappings)


def ensure_registration_reports(*args):
    from api.base import settings
    from addons.metadata import FULL_NAME
    from addons.metadata.report_format import REPORT_FORMATS
    from addons.metadata.utils import ensure_registration_report

    if FULL_NAME not in settings.INSTALLED_APPS:
        return

    for schema_name, report_name, csv_template in REPORT_FORMATS:
        ensure_registration_report(schema_name, report_name, csv_template)


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0253_ensure_schema_mappings'),
    ]

    operations = [
        UpdateRegistrationSchemasAndSchemaBlocks(),
        migrations.RunPython(ensure_registration_mappings, ensure_registration_mappings),
        migrations.RunPython(ensure_registration_reports, ensure_registration_reports),
    ]
