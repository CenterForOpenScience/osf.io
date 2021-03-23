import logging

from django.db import migrations

logger = logging.getLogger(__file__)
from osf.models import RegistrationSchema
from osf.utils.migrations import ensure_schemas
from website.project.metadata.schemas import ensure_schema_structure, from_json
from osf.utils.migrations import UpdateRegistrationSchemasAndSchemaBlocks
from api.base import settings
from osf.management.commands.migrate_pagecounter_data import FORWARD_SQL, REVERSE_SQL
from django.db import models

def add_schema(apps, schema_editor):
    schema = ensure_schema_structure(from_json('secondary-data.json'))

    RegistrationSchema.objects.filter(name=schema['name']).update(visible=False, active=True)


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0002_adminlogentry'),
    ]

    operations = [
        UpdateRegistrationSchemasAndSchemaBlocks(),
        migrations.RunPython(add_schema, ensure_schemas),
        migrations.RunSQL([
            'CREATE INDEX nodelog__node_id_date_desc on osf_nodelog (node_id, date DESC);',
            # 'VACUUM ANALYZE osf_nodelog;'  # Run this manually, requires ~3 min downtime
        ], [
            'DROP INDEX IF EXISTS nodelog__node_id_date_desc RESTRICT;',
        ]),
        migrations.RunSQL(FORWARD_SQL, REVERSE_SQL),
        migrations.RunSQL(
            """
            SELECT setval(pg_get_serial_sequence('"osf_abstractprovider_licenses_acceptable"','id'),
                        coalesce(max("id"), 1), max("id") IS NOT null)
            FROM "osf_abstractprovider_licenses_acceptable";
            SELECT setval(pg_get_serial_sequence('"osf_abstractprovider"','id'),
                        coalesce(max("id"), 1), max("id") IS NOT null)
            FROM "osf_abstractprovider";
            """,
            """
            SELECT setval(pg_get_serial_sequence('"osf_abstractprovider_licenses_acceptable"','id'), 1, max("id") IS NOT null)
            FROM "osf_abstractprovider_licenses_acceptable";
            SELECT setval(pg_get_serial_sequence('"osf_abstractprovider"','id'), 1, max("id") IS NOT null)
            FROM "osf_abstractprovider_licenses_acceptable";
            """
        ),
        migrations.RunSQL(
            [
                'ALTER TABLE "osf_abstractnode" ALTER COLUMN "access_requests_enabled" SET DEFAULT TRUE',
                'ALTER TABLE "osf_abstractnode" ALTER COLUMN "access_requests_enabled" DROP DEFAULT;',
            ],
            state_operations=[
                migrations.AlterField(
                    model_name='abstractnode',
                    name='access_requests_enabled',
                    field=models.NullBooleanField(default=True, db_index=True),
                )
            ],
        ),
        migrations.RunSQL(
            [
                """
                CREATE INDEX osf_abstractnode_registered_date_index ON public.osf_abstractnode (registered_date DESC);
                CREATE INDEX osf_abstractnode_registration_pub_del_type_index ON public.osf_abstractnode (is_public, is_deleted, type) WHERE is_public=TRUE and is_deleted=FALSE and type = 'osf.registration';
                CREATE INDEX osf_abstractnode_node_pub_del_type_index ON public.osf_abstractnode (is_public, is_deleted, type) WHERE is_public=TRUE and is_deleted=FALSE and type = 'osf.node';
                CREATE INDEX osf_abstractnode_collection_pub_del_type_index ON public.osf_abstractnode (is_public, is_deleted, type) WHERE is_public=TRUE and is_deleted=FALSE and type = 'osf.collection';
                """
            ],
            [
                """
                DROP INDEX public.osf_abstractnode_registered_date_index RESTRICT;
                DROP INDEX public.osf_abstractnode_registration_pub_del_type_index RESTRICT;
                DROP INDEX public.osf_abstractnode_node_pub_del_type_index RESTRICT;
                DROP INDEX public.osf_abstractnode_collection_pub_del_type_index RESTRICT;
                """
            ]
        ),
        migrations.RunSQL(
            [
                """
                CREATE UNIQUE INDEX osf_basefilenode_non_trashed_unique_index
                ON public.osf_basefilenode
                (target_object_id, name, parent_id, type, _path)
                WHERE type NOT IN ('osf.trashedfilenode', 'osf.trashedfile', 'osf.trashedfolder');
                """,
            ],
            [
                """
                DROP INDEX public.osf_basefilenode_non_trashed_unique_index RESTRICT;
                """
            ]
        ),
    ]
