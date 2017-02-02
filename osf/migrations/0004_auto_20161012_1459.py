# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-10-12 19:59
from __future__ import unicode_literals

from django.db import migrations, models
import osf.models.base


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0003_auto_20161012_1244'),
    ]

    operations = [
        migrations.AlterField(
            model_name='alternativecitation',
            name='_id',
            field=models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True),
        ),
        migrations.AlterField(
            model_name='apioauth2application',
            name='_id',
            field=models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True),
        ),
        migrations.AlterField(
            model_name='apioauth2personaltoken',
            name='_id',
            field=models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True),
        ),
        migrations.AlterField(
            model_name='apioauth2scope',
            name='_id',
            field=models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True),
        ),
        migrations.AlterField(
            model_name='archivejob',
            name='_id',
            field=models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True),
        ),
        migrations.AlterField(
            model_name='archivetarget',
            name='_id',
            field=models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True),
        ),
        migrations.AlterField(
            model_name='conference',
            name='_id',
            field=models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True),
        ),
        migrations.AlterField(
            model_name='draftregistration',
            name='_id',
            field=models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True),
        ),
        migrations.AlterField(
            model_name='draftregistrationapproval',
            name='_id',
            field=models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True),
        ),
        migrations.AlterField(
            model_name='draftregistrationlog',
            name='_id',
            field=models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True),
        ),
        migrations.AlterField(
            model_name='embargo',
            name='_id',
            field=models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True),
        ),
        migrations.AlterField(
            model_name='embargoterminationapproval',
            name='_id',
            field=models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True),
        ),
        migrations.AlterField(
            model_name='externalaccount',
            name='_id',
            field=models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True),
        ),
        migrations.AlterField(
            model_name='fileversion',
            name='_id',
            field=models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True),
        ),
        migrations.AlterField(
            model_name='identifier',
            name='_id',
            field=models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True),
        ),
        migrations.AlterField(
            model_name='institution',
            name='_id',
            field=models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True),
        ),
        migrations.AlterField(
            model_name='mailrecord',
            name='_id',
            field=models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True),
        ),
        migrations.AlterField(
            model_name='metaschema',
            name='_id',
            field=models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True),
        ),
        migrations.AlterField(
            model_name='nodelicense',
            name='_id',
            field=models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True),
        ),
        migrations.AlterField(
            model_name='nodelicenserecord',
            name='_id',
            field=models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True),
        ),
        migrations.AlterField(
            model_name='nodelog',
            name='_id',
            field=models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True),
        ),
        migrations.AlterField(
            model_name='noderelation',
            name='_id',
            field=models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True),
        ),
        migrations.AlterField(
            model_name='notificationdigest',
            name='_id',
            field=models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True),
        ),
        migrations.AlterField(
            model_name='preprintprovider',
            name='_id',
            field=models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True),
        ),
        migrations.AlterField(
            model_name='privatelink',
            name='_id',
            field=models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True),
        ),
        migrations.AlterField(
            model_name='queuedmail',
            name='_id',
            field=models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True),
        ),
        migrations.AlterField(
            model_name='registrationapproval',
            name='_id',
            field=models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True),
        ),
        migrations.AlterField(
            model_name='retraction',
            name='_id',
            field=models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True),
        ),
        migrations.AlterField(
            model_name='session',
            name='_id',
            field=models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True),
        ),
        migrations.AlterField(
            model_name='storedfilenode',
            name='_id',
            field=models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True),
        ),
        migrations.AlterField(
            model_name='subject',
            name='_id',
            field=models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True),
        ),
        migrations.AlterField(
            model_name='trashedfilenode',
            name='_id',
            field=models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True),
        ),
    ]
