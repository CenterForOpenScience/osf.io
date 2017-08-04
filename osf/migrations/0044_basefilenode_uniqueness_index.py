# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging

from django.db import connection
from django.db import migrations

logger = logging.getLogger(__name__)

def remove_duplicate_filenodes(*args):
    from osf.models.files import BaseFileNode
    sql = """
        SELECT id
        FROM (SELECT
                *,
                LEAD(row, 1)
                OVER () AS nextrow
              FROM (SELECT
                      *,
                      ROW_NUMBER()
                      OVER (w) AS row
                    FROM (SELECT *
                          FROM osf_basefilenode
                          WHERE (node_id IS NULL OR name IS NULL OR parent_id IS NULL OR type IS NULL OR _path IS NULL) AND
                                type NOT IN ('osf.trashedfilenode', 'osf.trashedfile', 'osf.trashedfolder')) AS null_files
                    WINDOW w AS (
                      PARTITION BY node_id, name, parent_id, type, _path
                      ORDER BY id )) AS x) AS y
        WHERE row > 1 OR nextrow > 1;
    """
    visited = []
    with connection.cursor() as cursor:
        cursor.execute(sql)
        dupes = BaseFileNode.objects.filter(id__in=[t[0] for t in cursor.fetchall()])
        logger.info('\nFound {} dupes, merging and removing'.format(dupes.count()))
        for dupe in dupes:
            visited.append(dupe.id)
            force = False
            next_dupe = dupes.exclude(id__in=visited).filter(node_id=dupe.node_id, name=dupe.name, parent_id=dupe.parent_id, type=dupe.type, _path=dupe._path).first()
            if dupe.node_id is None:
                # Bad data, force-delete
                force = True
            if not next_dupe:
                # Last one, don't delete
                continue
            if dupe.versions.count() > 1:
                logger.warn('{} Expected 0 or 1 versions, got {}'.format(dupe.id, dupe.versions.count()))
                # Don't modify versioned files
                continue
            for guid in list(dupe.guids.all()):
                guid.referent = next_dupe
                guid.save()
            if force:
                BaseFileNode.objects.filter(id=dupe.id).delete()
            else:
                dupe.delete()
    with connection.cursor() as cursor:
        logger.info('Validating clean-up success...')
        cursor.execute(sql)
        dupes = BaseFileNode.objects.filter(id__in=cursor.fetchall())
        if dupes.exists():
            logger.error('Dupes exist after migration, failing\n{}'.format(dupes.values_list('id', flat=True)))
    logger.info('Indexing...')

def noop(*args):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0043_set_share_title'),
    ]

    operations = [
        migrations.RunPython(remove_duplicate_filenodes, noop),
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
