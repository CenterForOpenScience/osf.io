# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('common_auth', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='myuser',
            name='osf_id',
            field=models.CharField(default=False, max_length=10, blank=True),
        ),
    ]
