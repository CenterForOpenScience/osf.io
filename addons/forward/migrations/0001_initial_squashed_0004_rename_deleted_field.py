# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2022-08-15 17:46
from __future__ import unicode_literals

import datetime
import dirtyfields.dirtyfields
from django.db import migrations, models
import django.db.models.deletion
from django.utils.timezone import utc
import django_extensions.db.fields
import osf.models.base
import osf.models.validators
import osf.utils.fields


class Migration(migrations.Migration):

    replaces = [('addons_forward', '0001_initial'), ('addons_forward', '0002_nodesettings_owner'), ('addons_forward', '0003_auto_20170713_1125'), ('addons_forward', '0004_rename_deleted_field')]

    dependencies = [
        ('osf', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='NodeSettings',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('_id', models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('url', models.URLField(blank=True, max_length=255, null=True)),
                ('label', models.TextField(blank=True, null=True, validators=[osf.models.validators.validate_no_html])),
                ('owner', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='addons_forward_node_settings', to='osf.AbstractNode')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, default=datetime.datetime(1970, 1, 1, 0, 0, tzinfo=utc), verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('deleted', osf.utils.fields.NonNaiveDateTimeField(blank=True, null=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(dirtyfields.dirtyfields.DirtyFieldsMixin, models.Model),
        ),
    ]
