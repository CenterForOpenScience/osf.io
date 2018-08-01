# -*- coding: utf-8 -*-
# Note:
# This migration is skippable if `scripts/premigrate_created_modified.py`
# is utilized. It allows the larger of these tables to be updated asynchronously without downtime.
# It requires not releasing these model changes until the beat tasks are approximately complete.

import logging

from django.db import migrations
import django.utils.timezone
import django_extensions.db.fields
import osf.utils.fields
from website import settings

logger = logging.getLogger(__file__)

PREMIGRATED = '1-minute-incremental-migrations' in settings.CeleryConfig.beat_schedule

def finalize_premigrated(state, schema):
    from scripts.premigrate_created_modified import finalize_migration
    logger.info('Finalizing pre-migraiton')
    finalize_migration()

OPERATIONS = [
    migrations.AlterModelOptions(
        name='fileversion',
        options={'ordering': ('-created',)},
    ),
    migrations.RenameField(
        model_name='action',
        old_name='date_modified',
        new_name='modified',
    ),
    migrations.RenameField(
        model_name='action',
        old_name='date_created',
        new_name='created',
    ),
    migrations.RenameField(
        model_name='fileversion',
        old_name='date_modified',
        new_name='external_modified',
    ),
    migrations.RenameField(
        model_name='abstractnode',
        old_name='date_created',
        new_name='created',
    ),
    migrations.RenameField(
        model_name='abstractnode',
        old_name='date_modified',
        new_name='last_logged',
    ),
    migrations.RenameField(
        model_name='apioauth2application',
        old_name='date_created',
        new_name='created',
    ),
    migrations.RenameField(
        model_name='comment',
        old_name='date_created',
        new_name='created',
    ),
    migrations.RenameField(
        model_name='comment',
        old_name='date_modified',
        new_name='modified',
    ),
    migrations.RenameField(
        model_name='fileversion',
        old_name='date_created',
        new_name='created',
    ),
    migrations.RenameField(
        model_name='preprintservice',
        old_name='date_created',
        new_name='created',
    ),
    migrations.RenameField(
        model_name='preprintservice',
        old_name='date_modified',
        new_name='modified'
    ),
    migrations.RenameField(
        model_name='privatelink',
        old_name='date_created',
        new_name='created',
    ),
    migrations.RenameField(
        model_name='session',
        old_name='date_created',
        new_name='created',
    ),
    migrations.RenameField(
        model_name='session',
        old_name='date_modified',
        new_name='modified',
    ),
    migrations.AddField(
        model_name='abstractnode',
        name='modified',
        field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
    ),
    migrations.AddField(
        model_name='apioauth2application',
        name='modified',
        field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
    ),
    migrations.AddField(
        model_name='apioauth2personaltoken',
        name='created',
        field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='created'),
        preserve_default=False,
    ),
    migrations.AddField(
        model_name='apioauth2personaltoken',
        name='modified',
        field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
    ),
    migrations.AddField(
        model_name='apioauth2scope',
        name='created',
        field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='created'),
        preserve_default=False,
    ),
    migrations.AddField(
        model_name='apioauth2scope',
        name='modified',
        field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
    ),
    migrations.AddField(
        model_name='archivejob',
        name='created',
        field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='created'),
        preserve_default=False,
    ),
    migrations.AddField(
        model_name='archivejob',
        name='modified',
        field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
    ),
    migrations.AddField(
        model_name='archivetarget',
        name='created',
        field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='created'),
        preserve_default=False,
    ),
    migrations.AddField(
        model_name='archivetarget',
        name='modified',
        field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
    ),
    migrations.AddField(
        model_name='basefilenode',
        name='created',
        field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='created'),
        preserve_default=False,
    ),
    migrations.AddField(
        model_name='basefilenode',
        name='modified',
        field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
    ),
    migrations.AddField(
        model_name='blacklistguid',
        name='created',
        field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='created'),
        preserve_default=False,
    ),
    migrations.AddField(
        model_name='blacklistguid',
        name='modified',
        field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
    ),
    migrations.AddField(
        model_name='citationstyle',
        name='created',
        field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='created'),
        preserve_default=False,
    ),
    migrations.AddField(
        model_name='citationstyle',
        name='modified',
        field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
    ),
    migrations.AddField(
        model_name='conference',
        name='created',
        field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='created'),
        preserve_default=False,
    ),
    migrations.AddField(
        model_name='conference',
        name='modified',
        field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
    ),
    migrations.AddField(
        model_name='draftregistration',
        name='created',
        field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='created'),
        preserve_default=False,
    ),
    migrations.AddField(
        model_name='draftregistration',
        name='modified',
        field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
    ),
    migrations.AddField(
        model_name='draftregistrationapproval',
        name='created',
        field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='created'),
        preserve_default=False,
    ),
    migrations.AddField(
        model_name='draftregistrationapproval',
        name='modified',
        field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
    ),
    migrations.AddField(
        model_name='draftregistrationlog',
        name='created',
        field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='created'),
        preserve_default=False,
    ),
    migrations.AddField(
        model_name='draftregistrationlog',
        name='modified',
        field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
    ),
    migrations.AddField(
        model_name='embargo',
        name='created',
        field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='created'),
        preserve_default=False,
    ),
    migrations.AddField(
        model_name='embargo',
        name='modified',
        field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
    ),
    migrations.AddField(
        model_name='embargoterminationapproval',
        name='created',
        field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='created'),
        preserve_default=False,
    ),
    migrations.AddField(
        model_name='embargoterminationapproval',
        name='modified',
        field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
    ),
    migrations.AddField(
        model_name='externalaccount',
        name='created',
        field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='created'),
        preserve_default=False,
    ),
    migrations.AddField(
        model_name='externalaccount',
        name='modified',
        field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
    ),
    migrations.AddField(
        model_name='fileversion',
        name='modified',
        field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
    ),
    migrations.AddField(
        model_name='guid',
        name='modified',
        field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
    ),
    migrations.AddField(
        model_name='identifier',
        name='created',
        field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='created'),
        preserve_default=False,
    ),
    migrations.AddField(
        model_name='identifier',
        name='modified',
        field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
    ),
    migrations.AddField(
        model_name='institution',
        name='created',
        field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='created'),
        preserve_default=False,
    ),
    migrations.AddField(
        model_name='institution',
        name='last_logged',
        field=osf.utils.fields.NonNaiveDateTimeField(blank=True, db_index=True, default=django.utils.timezone.now, null=True),
    ),
    migrations.AddField(
        model_name='institution',
        name='modified',
        field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
    ),
    migrations.AddField(
        model_name='mailrecord',
        name='created',
        field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='created'),
        preserve_default=False,
    ),
    migrations.AddField(
        model_name='mailrecord',
        name='modified',
        field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
    ),
    migrations.AddField(
        model_name='metaschema',
        name='created',
        field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='created'),
        preserve_default=False,
    ),
    migrations.AddField(
        model_name='metaschema',
        name='modified',
        field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
    ),
    migrations.AddField(
        model_name='nodelicense',
        name='created',
        field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='created'),
        preserve_default=False,
    ),
    migrations.AddField(
        model_name='nodelicense',
        name='modified',
        field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
    ),
    migrations.AddField(
        model_name='nodelicenserecord',
        name='created',
        field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='created'),
        preserve_default=False,
    ),
    migrations.AddField(
        model_name='nodelicenserecord',
        name='modified',
        field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
    ),
    migrations.AddField(
        model_name='nodelog',
        name='created',
        field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='created'),
        preserve_default=False,
    ),
    migrations.AddField(
        model_name='nodelog',
        name='modified',
        field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
    ),
    migrations.AddField(
        model_name='noderelation',
        name='created',
        field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='created'),
        preserve_default=False,
    ),
    migrations.AddField(
        model_name='noderelation',
        name='modified',
        field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
    ),
    migrations.AddField(
        model_name='notificationdigest',
        name='created',
        field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='created'),
        preserve_default=False,
    ),
    migrations.AddField(
        model_name='notificationdigest',
        name='modified',
        field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
    ),
    migrations.AddField(
        model_name='notificationsubscription',
        name='created',
        field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='created'),
        preserve_default=False,
    ),
    migrations.AddField(
        model_name='notificationsubscription',
        name='modified',
        field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
    ),
    migrations.AddField(
        model_name='osfuser',
        name='created',
        field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='created'),
        preserve_default=False,
    ),
    migrations.AddField(
        model_name='osfuser',
        name='modified',
        field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
    ),
    migrations.AddField(
        model_name='pagecounter',
        name='created',
        field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='created'),
        preserve_default=False,
    ),
    migrations.AddField(
        model_name='pagecounter',
        name='modified',
        field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
    ),
    migrations.AddField(
        model_name='preprintprovider',
        name='created',
        field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='created'),
        preserve_default=False,
    ),
    migrations.AddField(
        model_name='preprintprovider',
        name='modified',
        field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
    ),
    migrations.AddField(
        model_name='privatelink',
        name='modified',
        field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
    ),
    migrations.AddField(
        model_name='queuedmail',
        name='created',
        field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='created'),
        preserve_default=False,
    ),
    migrations.AddField(
        model_name='queuedmail',
        name='modified',
        field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
    ),
    migrations.AddField(
        model_name='registrationapproval',
        name='created',
        field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='created'),
        preserve_default=False,
    ),
    migrations.AddField(
        model_name='registrationapproval',
        name='modified',
        field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
    ),
    migrations.AddField(
        model_name='retraction',
        name='created',
        field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='created'),
        preserve_default=False,
    ),
    migrations.AddField(
        model_name='retraction',
        name='modified',
        field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
    ),
    migrations.AddField(
        model_name='subject',
        name='created',
        field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='created'),
        preserve_default=False,
    ),
    migrations.AddField(
        model_name='subject',
        name='modified',
        field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
    ),
    migrations.AddField(
        model_name='tag',
        name='created',
        field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='created'),
        preserve_default=False,
    ),
    migrations.AddField(
        model_name='tag',
        name='modified',
        field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
    ),
    migrations.AddField(
        model_name='useractivitycounter',
        name='created',
        field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='created'),
        preserve_default=False,
    ),
    migrations.AddField(
        model_name='useractivitycounter',
        name='modified',
        field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
    ),
    migrations.AlterField(
        model_name='action',
        name='created',
        field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created'),
    ),
    migrations.AlterField(
        model_name='action',
        name='modified',
        field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
    ),
] if not PREMIGRATED else [migrations.RunPython(finalize_premigrated)]

class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0068_creator_modified_renames'),
    ]

    operations = OPERATIONS
