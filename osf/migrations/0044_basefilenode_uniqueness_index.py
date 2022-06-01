# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging

from django.db import migrations

logger = logging.getLogger(__name__)


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0043_set_share_title'),
    ]

    operations = [
        migrations.RunSQL(
            [
                """
                CREATE UNIQUE INDEX active_file_node_path_name_type_unique_index
                ON public.osf_basefilenode (node_id, _path, name, type)
                WHERE (type NOT IN ('osf.trashedfilenode', 'osf.trashedfile', 'osf.trashedfolder')
                  AND parent_id IS NULL);
                """
            ], [
                """
                DROP INDEX IF EXISTS active_file_node_path_name_type_unique_index RESTRICT;
                """
            ]
        )
    ]
