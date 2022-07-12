# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0221_ensure_schema_and_reports'),
    ]

    operations = [
        migrations.AddField(
            model_name='registrationschemablock',
            name='default',
            field=models.BooleanField(default=False),
        ),
    ]
