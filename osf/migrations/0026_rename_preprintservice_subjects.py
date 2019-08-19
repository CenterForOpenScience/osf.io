# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2017-04-17 22:49
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0025_migrate_preprint_subjects_to_fks'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='preprintservice',
            name='subjects',
        ),
        migrations.RenameField(
            model_name='preprintservice',
            old_name='_subjects',
            new_name='subjects',
        ),
    ]
