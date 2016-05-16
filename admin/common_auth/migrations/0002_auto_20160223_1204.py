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
            name='desk_email',
            field=models.EmailField(default=b'', max_length=255, verbose_name=b'desk_email'),
        ),
        migrations.AddField(
            model_name='myuser',
            name='desk_password',
            field=models.CharField(default=b'', max_length=128, verbose_name=b'desk_password'),
        ),
    ]
