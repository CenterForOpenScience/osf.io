# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0225_add_pattern_and_norm_to_registration_schema_block'),
    ]

    operations = [
        migrations.AlterField(
            model_name='FileLog',
            name='path',
            field=models.TextField(null=True),
        ),
    ]
