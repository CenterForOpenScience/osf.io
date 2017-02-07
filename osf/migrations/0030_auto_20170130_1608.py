# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2017-01-30 22:08
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0029_externalaccount_date_last_refreshed'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='conference',
            options={'permissions': (('view_conference', 'Can view conference details in the admin app.'),)},
        ),
        migrations.AlterModelOptions(
            name='node',
            options={'permissions': (('view_node', 'Can view node details'),)},
        ),
        migrations.AlterModelOptions(
            name='osfuser',
            options={'permissions': (('view_user', 'Can view user details'),)},
        ),
        migrations.AlterModelOptions(
            name='registration',
            options={'permissions': (('view_registration', 'Can view registration details'),)},
        ),
    ]
