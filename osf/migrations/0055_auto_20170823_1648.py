# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-08-23 21:48
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0054_auto_20170823_1555'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='abstractnode',
            name='alternative_citations',
        ),
        migrations.DeleteModel(
            name='AlternativeCitation',
        ),
    ]
