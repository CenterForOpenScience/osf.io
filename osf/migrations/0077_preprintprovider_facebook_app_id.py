# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-01-31 21:43
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0076_action_rename'),
    ]

    operations = [
        migrations.AddField(
            model_name='preprintprovider',
            name='facebook_app_id',
            field=models.BigIntegerField(blank=True, null=True),
        ),
    ]
