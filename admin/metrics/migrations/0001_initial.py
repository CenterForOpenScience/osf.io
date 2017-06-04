# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='OSFWebsiteStatistics',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('users', models.IntegerField(default=0, verbose_name=b'OSF users')),
                ('delta_users', models.IntegerField(default=0)),
                ('unregistered_users', models.IntegerField(default=0, verbose_name=b'Unregistered users')),
                ('projects', models.IntegerField(default=0, verbose_name=b'Number of projects')),
                ('delta_projects', models.IntegerField(default=0)),
                ('public_projects', models.IntegerField(default=0, verbose_name=b'Number of public projects')),
                ('delta_public_projects', models.IntegerField(default=0)),
                ('registered_projects', models.IntegerField(default=0, verbose_name=b'Number of projects registered')),
                ('delta_registered_projects', models.IntegerField(default=0)),
                ('date', models.DateTimeField(default=None)),
            ],
        ),
    ]
