# -*- coding: utf-8 -*-
# Generated by Django 1.11.28 on 2021-10-07 02:25
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0238_abstractprovider_allow_updates'),
    ]

    operations = [
        migrations.AddField(
            model_name='abstractprovider',
            name='allow_bulk_uploads',
            field=models.NullBooleanField(default=False),
        ),
    ]