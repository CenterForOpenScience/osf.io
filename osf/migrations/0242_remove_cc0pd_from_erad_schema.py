# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
import logging

from django.db import migrations
from osf.utils.migrations import UpdateRegistrationSchemasAndSchemaBlocks

logger = logging.getLogger(__name__)


def noop(*args):
    pass


def ensure_registration_mappings(*args):
    from api.base import settings
    from addons.weko.apps import NAME
    from addons.weko.utils import ensure_registration_metadata_mapping
    from addons.weko.mappings import REGISTRATION_METADATA_MAPPINGS
    if NAME not in settings.INSTALLED_APPS:
        return
    for schema_name, mappings in REGISTRATION_METADATA_MAPPINGS:
        ensure_registration_metadata_mapping(schema_name, mappings)


def ensure_registration_reports(*args):
    from api.base import settings
    from addons.metadata import FULL_NAME
    from addons.metadata.utils import ensure_registration_report
    from addons.metadata.report_format import REPORT_FORMATS
    if FULL_NAME not in settings.INSTALLED_APPS:
        return
    for schema_name, report_name, csv_template in REPORT_FORMATS:
        ensure_registration_report(schema_name, report_name, csv_template)


def migrate_CC0PD_to_CC0_for_filemetadata(*args):
    from addons.metadata.models import FileMetadata
    filemetadatas = FileMetadata.objects.filter(metadata__isnull=False)
    for filemetadata in filemetadatas:
        try:
            metadata = json.loads(filemetadata.metadata)
        except json.JSONDecodeError:
            logger.warning('Skipped: Failed to parse JSON for file metadata {} of path "{}" of "{}"'.format(
                filemetadata._id,
                filemetadata.path,
                filemetadata.project.owner._id
            ), exc_info=True)
            continue
        cc0pd_items = [
            item
            for item in metadata['items']
            if item.get('data', {}).get('grdm-file:data-policy-license', {}).get('value', '') == 'CC0PD'
        ]
        if len(cc0pd_items) == 0:
            continue
        for item in cc0pd_items:
            item['data']['grdm-file:data-policy-license']['value'] = 'CC0'
        filemetadata.metadata = json.dumps(metadata)
        filemetadata.save()
        logger.info('Migrated: Fixed CC0PD to CC0 for file metadata {} of path "{}" of "{}"'.format(
            filemetadata._id,
            filemetadata.path,
            filemetadata.project.owner._id
        ))


def migrate_CC0PD_to_CC0_for_registration(*args):
    from osf.models import Registration
    registrations = Registration.objects.filter(registered_meta__isnull=False)
    for registration in registrations:
        dirty = False
        for meta_key, meta_value in registration.registered_meta.items():
            meta_dirty = False
            try:
                filemetadatas = json.loads(meta_value.get('grdm-files', {}).get('value', '[]'))
            except json.JSONDecodeError:
                logger.error('Skipped: Failed to parse JSON for registered metadata {} of "{}"'.format(
                    registration._id,
                    registration.registered_from._id,
                ), exc_info=True)
                continue
            for filemetadata in filemetadatas:
                license = filemetadata.get('metadata', {}).get('grdm-file:data-policy-license', {}).get('value', '')
                if license == 'CC0PD':
                    filemetadata['metadata']['grdm-file:data-policy-license']['value'] = 'CC0'
                    meta_dirty = True
            if not meta_dirty:
                continue
            dirty = True
            meta_value['grdm-files']['value'] = json.dumps(filemetadatas)
            registration.registered_meta[meta_key] = meta_value
        if not dirty:
            continue
        registration.save()
        logger.info('Migrated: Fixed CC0PD to CC0 for registered metadata {} of "{}"'.format(
            registration._id,
            registration.registered_from._id,
        ))


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0241_ensure_schema_mappings'),
    ]

    operations = [
        UpdateRegistrationSchemasAndSchemaBlocks(),
        migrations.RunPython(migrate_CC0PD_to_CC0_for_filemetadata, noop),
        migrations.RunPython(migrate_CC0PD_to_CC0_for_registration, noop),
        migrations.RunPython(ensure_registration_reports, ensure_registration_reports),
        migrations.RunPython(ensure_registration_mappings, ensure_registration_mappings),
    ]
