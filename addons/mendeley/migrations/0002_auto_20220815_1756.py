# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2022-08-15 17:56
from __future__ import unicode_literals

from django.db import migrations
import django_extensions.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('addons_mendeley', '0001_initial_squashed_0004_rename_deleted_field'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usersettings',
            name='created',
            field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created'),
        ),
    ]
