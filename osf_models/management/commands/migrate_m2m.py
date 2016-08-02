from __future__ import print_function
from __future__ import unicode_literals

from datetime import datetime

from django.core.management.base import BaseCommand
from osf_models.scripts.migrate_nodes import (build_pk_caches,
                                              set_node_many_to_many_on_nodes,
                                              set_node_many_to_many_on_users,
                                              set_system_tag_many_to_many_on_users,
                                              set_tag_many_to_many_on_nodes,
                                              set_user_many_to_many_on_nodes,
                                              set_user_many_to_many_on_users)

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

        # m2m
        set_node_many_to_many_on_nodes()
        set_user_many_to_many_on_nodes()
        set_node_many_to_many_on_users()
        set_user_many_to_many_on_users()
        set_system_tag_many_to_many_on_users()
        set_tag_many_to_many_on_nodes()

        print('Finished in {} seconds...'.format((datetime.now() - start
                                                  ).total_seconds()))
