from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0002_adminlogentry'),
    ]

    operations = [
        migrations.RunSQL(
            [
                """
                CREATE UNIQUE INDEX one_quickfiles_per_user ON public.osf_abstractnode USING btree (creator_id, type, is_deleted) WHERE (((type)::text = 'osf.quickfilesnode'::text) AND (is_deleted = false));
                CREATE INDEX osf_abstractnode_collection_pub_del_type_index ON public.osf_abstractnode USING btree (is_public, is_deleted, type) WHERE ((is_public = true) AND (is_deleted = false) AND ((type)::text = 'osf.collection'::text));
                CREATE INDEX osf_abstractnode_date_modified_ef1e2ad8 ON public.osf_abstractnode USING btree (last_logged);
                CREATE INDEX osf_abstractnode_node_pub_del_type_index ON public.osf_abstractnode USING btree (is_public, is_deleted, type) WHERE ((is_public = true) AND (is_deleted = false) AND ((type)::text = 'osf.node'::text));
                CREATE INDEX osf_abstractnode_registered_date_index ON public.osf_abstractnode USING btree (registered_date DESC);
                CREATE INDEX osf_abstractnode_registration_pub_del_type_index ON public.osf_abstractnode USING btree (is_public, is_deleted, type) WHERE ((is_public = true) AND (is_deleted = false) AND ((type)::text = 'osf.registration'::text));
                CREATE INDEX fileversion_date_created_desc ON public.osf_fileversion USING btree (created DESC);
                CREATE INDEX fileversion_metadata_sha_arch_vault_index ON public.osf_fileversion USING btree (((metadata -> 'sha256'::text)), ((metadata -> 'archive'::text)), ((metadata -> 'vault'::text)));
                CREATE INDEX nodelog__node_id_date_desc ON public.osf_nodelog USING btree (node_id, date DESC);
                CREATE INDEX osf_nodelog_should_hide_nid ON public.osf_nodelog USING btree (should_hide, node_id);
                CREATE UNIQUE INDEX osf_noderequest_target_creator_non_accepted ON public.osf_noderequest USING btree (target_id, creator_id) WHERE ((machine_state)::text <> 'accepted'::text);
                CREATE INDEX lowercase_tag_index ON public.osf_tag USING btree (lower((name)::text), system);
                """
            ],
            []
        ),
    ]
