# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('addons_metadata', '0004_remove_usersettings_erad_researcher_number'),
    ]

    operations = [
        migrations.AlterField(
            model_name='eradrecord',
            name='kenkyusha_no',
            field=models.TextField(blank=True, db_index=True, null=True),
        ),
        migrations.AddIndex(
            model_name='eradrecord',
            index=models.Index(fields=['kenkyusha_no', 'kadai_id', 'nendo'], name='addons_meta_kenkyus_1e859e_idx'),
        ),
    ]
