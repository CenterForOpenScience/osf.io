# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2020-01-21 17:39
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0197_add_ab_testing_home_page_hero_text_version_b_flag'),
    ]

    operations = [
        migrations.AddField(
            model_name='abstractprovider',
            name='in_sloan_study',
            field=models.NullBooleanField(default=True),
        ),
    ]
