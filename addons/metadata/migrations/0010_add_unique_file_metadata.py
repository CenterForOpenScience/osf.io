# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('addons_metadata', '0009_remove_duplicated_file_metadata'),
    ]

    operations = [
        migrations.RunSQL(
            [
                '''
                CREATE UNIQUE INDEX filemetadata_project_id_path
                ON addons_metadata_filemetadata (project_id, path);
                ''',
            ],
            [
                '''
                DROP INDEX filemetadata_project_id_path RESTRICT;
                ''',
            ]
        ),
    ]
