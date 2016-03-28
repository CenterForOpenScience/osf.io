# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('conferences', '0002_auto_20160226_1055'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='conference',
            name='field_names',
        ),
        migrations.DeleteModel(
            name='Conference',
        ),
        migrations.DeleteModel(
            name='ConferenceFieldNames',
        ),
    ]
