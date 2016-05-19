# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('admin', '0001_initial'),
        ('common_auth', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='OSFLogEntry',
            fields=[
                ('logentry_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='admin.LogEntry')),
            ],
            bases=('admin.logentry',),
        ),
    ]
