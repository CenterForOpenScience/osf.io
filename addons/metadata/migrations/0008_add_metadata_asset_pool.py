# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields
import osf.models.base
import osf.utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('addons_metadata', '0007_user_to_file_metadata'),
    ]

    operations = [
        migrations.CreateModel(
            name='MetadataAssetPool',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('project', models.ForeignKey(blank=True, null=True,
                                              on_delete=django.db.models.deletion.CASCADE,
                                              related_name='metadata_asset_pool', to='addons_metadata.NodeSettings')),
                ('path', models.TextField()),
                ('metadata', models.TextField(blank=True, null=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, osf.models.base.QuerySetExplainMixin),
        ),
    ]
