# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-03-05 20:22
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0087_migrate_collections_data'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='abstractnode',
            name='is_bookmark_collection',
        ),
        migrations.AlterField(
            model_name='abstractnode',
            name='type',
            field=models.CharField(choices=[('osf.node', 'node'), ('osf.registration', 'registration')], db_index=True, max_length=255),
        ),
    ]
