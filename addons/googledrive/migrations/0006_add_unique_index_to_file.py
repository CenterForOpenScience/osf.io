# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('addons_googledrive', '0005_remove_duplicated_file'),
    ]

    operations = [
        migrations.RunSQL(
            [
                """
                CREATE UNIQUE INDEX osf_googledrive_file_unique_index
                ON osf_basefilenode(target_object_id, type, _path)
                WHERE type IN ('osf.googledrivefile', 'osf.googledrivefolder');
                """,
            ],
            [
                """
                DROP INDEX osf_googledrive_file_unique_index RESTRICT;
                """,
            ],
        ),
    ]
