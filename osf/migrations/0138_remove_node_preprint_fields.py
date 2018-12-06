# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2018-06-08 03:52
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0137_transfer_preprint_service_permissions'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='abstractnode',
            name='_has_abandoned_preprint',
        ),
        migrations.RemoveField(
            model_name='abstractnode',
            name='_is_preprint_orphan',
        ),
        migrations.RemoveField(
            model_name='abstractnode',
            name='preprint_article_doi',
        ),
        migrations.RemoveField(
            model_name='abstractnode',
            name='preprint_file',
        ),
    ]
