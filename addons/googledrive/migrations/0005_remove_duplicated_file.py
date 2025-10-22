# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('addons_googledrive', '0004_rename_deleted_field'),
        ('osf', '0085_finalize_file_node_to_target'),
    ]

    operations = [
        migrations.RunSQL(
            [
                # Remove duplicates of basefilenode of GoogleDrive type
                """
                DELETE FROM osf_basefilenode as a
                WHERE a.type IN ('osf.googledrivefile', 'osf.googledrivefolder')
                AND EXISTS (
                    SELECT 1 FROM osf_basefilenode as b
                    WHERE a.target_object_id = b.target_object_id
                    AND a.type = b.type
                    AND a._path = b._path
                    AND a.modified < b.modified
                );
                """,
            ],
            migrations.RunSQL.noop,
        ),
    ]
