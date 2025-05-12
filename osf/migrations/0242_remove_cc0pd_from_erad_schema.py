# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
import logging

from django.db import migrations
from osf.utils.migrations import UpdateRegistrationSchemasAndSchemaBlocks


logger = logging.getLogger(__name__)
TARGET_SCHEMA_NAME = '公的資金による研究データのメタデータ登録'


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
    from osf.models.metaschema import RegistrationSchema
    schemas = list(RegistrationSchema.objects.filter(name=TARGET_SCHEMA_NAME))
    if len(schemas) == 0:
        logger.warning(f'Skipped: Failed to find schema "{TARGET_SCHEMA_NAME}"')
        return
    schema_ids = [schema._id for schema in schemas]
    filemetadatas = FileMetadata.objects.filter(metadata__isnull=False)
    logger.info('Found {} file metadatas'.format(filemetadatas.count()))
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
            if item.get('schema', None) in schema_ids and item.get('data', {}).get('grdm-file:data-policy-license', {}).get('value', '') == 'CC0PD'
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
    logger.info('Finished migration')


def _fix_CC0PD_to_CC0_for_filemetadata(filemetadatas):
    meta_dirty = False
    for filemetadata in filemetadatas:
        license = filemetadata.get('metadata', {}).get('grdm-file:data-policy-license', {}).get('value', '')
        if license == 'CC0PD':
            filemetadata['metadata']['grdm-file:data-policy-license']['value'] = 'CC0'
            meta_dirty = True
    return meta_dirty


def migrate_CC0PD_to_CC0_for_registration(*args):
    from osf.models import Registration
    from osf.models.metaschema import RegistrationSchema
    schemas = list(RegistrationSchema.objects.filter(name=TARGET_SCHEMA_NAME))
    if len(schemas) == 0:
        logger.warning(f'Skipped: Failed to find schema "{TARGET_SCHEMA_NAME}"')
        return
    registrations = Registration.objects.filter(
        registered_meta__isnull=False,
        registered_schema__in=schemas
    )
    logger.info('Found {} registrations'.format(registrations.count()))
    for registration in registrations:
        dirty = False
        for meta_key, meta_value in registration.registered_meta.items():
            try:
                filemetadatas = json.loads(meta_value.get('grdm-files', {}).get('value', '[]'))
            except json.JSONDecodeError:
                logger.warning('Skipped: Failed to parse JSON for registered metadata {} of "{}"'.format(
                    registration._id,
                    registration.registered_from._id,
                ), exc_info=True)
                continue
            if not _fix_CC0PD_to_CC0_for_filemetadata(filemetadatas):
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
    logger.info('Finished migration')


def migrate_CC0PD_to_CC0_for_draft_registration(*args):
    from osf.models import DraftRegistration
    from osf.models.metaschema import RegistrationSchema
    schemas = list(RegistrationSchema.objects.filter(name=TARGET_SCHEMA_NAME))
    if len(schemas) == 0:
        logger.warning(f'Skipped: Failed to find schema "{TARGET_SCHEMA_NAME}"')
        return
    draft_registrations = DraftRegistration.objects.filter(
        registration_metadata__isnull=False,
        registration_schema__in=schemas
    )
    logger.info('Found {} draft registrations'.format(draft_registrations.count()))
    for draft_registration in draft_registrations:
        meta_value = draft_registration.registration_metadata
        try:
            file_list = meta_value.get('grdm-files', {}).get('value', '[]')
            if len(file_list) == 0:
                continue
            filemetadatas = json.loads(file_list)
        except json.JSONDecodeError:
            logger.warning('Skipped: Failed to parse JSON for draft registration metadata {} of "{}"'.format(
                draft_registration._id,
                draft_registration.branched_from._id,
            ), exc_info=True)
            logger.info(meta_value.get('grdm-files', {}).get('value', '[]'))
            continue
        if not _fix_CC0PD_to_CC0_for_filemetadata(filemetadatas):
            continue
        meta_value['grdm-files']['value'] = json.dumps(filemetadatas)
        draft_registration.save()
        logger.info('Migrated: Fixed CC0PD to CC0 for draft registration metadata {} of "{}"'.format(
            draft_registration._id,
            draft_registration.branched_from._id,
        ))
    logger.info('Finished migration')


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0241_ensure_schema_mappings'),
    ]

    operations = [
        UpdateRegistrationSchemasAndSchemaBlocks(),
        migrations.RunPython(migrate_CC0PD_to_CC0_for_filemetadata, noop),
        migrations.RunPython(migrate_CC0PD_to_CC0_for_registration, noop),
        migrations.RunPython(migrate_CC0PD_to_CC0_for_draft_registration, noop),
        migrations.RunPython(ensure_registration_reports, ensure_registration_reports),
        migrations.RunPython(ensure_registration_mappings, ensure_registration_mappings),
    ]
