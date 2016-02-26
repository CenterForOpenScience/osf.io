# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='OSFStatistic',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('users', models.IntegerField(verbose_name=b'OSF users')),
                ('date', models.DateTimeField(default=datetime.datetime(2016, 2, 26, 18, 56, 11, 579744))),
            ],
        ),
    ]
