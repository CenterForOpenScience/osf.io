# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0144_add_prereg_winddown_switches'),
    ]

    operations = [
        migrations.AddField(
            model_name='registrationschema',
            name='visible',
            field=models.BooleanField(default=True),
        ),
    ]
