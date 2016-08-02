from __future__ import print_function
from __future__ import unicode_literals

from datetime import datetime

from django.core.management.base import BaseCommand
from osf_models.scripts.migrate_nodes import (build_pk_caches,
                                              set_node_foreign_keys_on_nodes,
                                              set_user_foreign_keys_on_nodes,
                                              set_user_foreign_keys_on_users,
                                              set_retraction_foreign_keys_on_nodes,
                                              set_embargo_foreign_keys_on_nodes)

from website.app import init_app


class Command(BaseCommand):
    help = 'Migrates data from tokumx to postgres'

    def handle(self, *args, **options):
        print('Initializing Flask App...')
        init_app()
        start = datetime.now()

        global modm_to_django
        modm_to_django = build_pk_caches()
        print('Cached {} MODM to django mappings...'.format(len(
            modm_to_django.keys())))

        # fk
        set_node_foreign_keys_on_nodes()
        set_retraction_foreign_keys_on_nodes()
        set_embargo_foreign_keys_on_nodes()
        set_user_foreign_keys_on_nodes()
        set_user_foreign_keys_on_users()

        print('Finished in {} seconds...'.format((datetime.now() - start
                                                  ).total_seconds()))
