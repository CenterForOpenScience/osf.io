# -*- coding: utf-8 -*-
# Generated by Django 1.11.28 on 2022-02-08 16:15
from __future__ import unicode_literals

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0242_auto_20220125_1604'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notificationdigest',
            name='node_lineage',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=50), size=None),
        ),
    ]
