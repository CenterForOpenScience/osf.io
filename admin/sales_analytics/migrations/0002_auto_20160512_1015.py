# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-05-12 10:15
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sales_analytics', '0001_initial'),
    ]

    operations = [
        migrations.DeleteModel(
            name='DBMetrics',
        ),
        migrations.AlterUniqueTogether(
            name='usercount',
            unique_together=set([('date', 'tag')]),
        ),
    ]
