# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-08-18 20:41
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0053_auto_20170817_1056'),
    ]

    operations = [
        migrations.AddField(
            model_name='preprintservice',
            name='date_last_transitioned',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
    ]
