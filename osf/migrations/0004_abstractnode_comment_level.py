# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2017-04-02 21:47
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0003_auto_20170402_1611'),
    ]

    operations = [
        migrations.AddField(
            model_name='abstractnode',
            name='comment_level',
            field=models.CharField(default='public', max_length=10),
        ),
    ]
