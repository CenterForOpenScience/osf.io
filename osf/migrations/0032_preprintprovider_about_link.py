# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2017-02-07 00:43
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0031_auto_20170202_0943'),
    ]

    operations = [
        migrations.AddField(
            model_name='preprintprovider',
            name='about_link',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
    ]
