# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-05-11 18:46
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations
import osf.utils.datetime_aware_jsonfield


class Migration(migrations.Migration):

    dependencies = [
        ('addons_github', '0002_auto_20170323_1534'),
    ]

    operations = [
        migrations.AlterField(
            model_name='nodesettings',
            name='registration_data',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=dict, encoder=osf.utils.datetime_aware_jsonfield.DateTimeAwareJSONEncoder, null=True),
        ),
        migrations.AlterField(
            model_name='usersettings',
            name='oauth_grants',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=dict, encoder=osf.utils.datetime_aware_jsonfield.DateTimeAwareJSONEncoder),
        ),
    ]
