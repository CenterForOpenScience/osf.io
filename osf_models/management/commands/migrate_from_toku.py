from __future__ import print_function

from __future__ import unicode_literals

from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from osf_models.scripts.load_blacklist_guids import \
    main as load_blacklist_guids
from osf_models.scripts.load_guids import main as load_guids
from osf_models.scripts.migrate_nodelogs import main as migrate_nodelogs
from osf_models.scripts.migrate_nodes import (build_pk_caches,
                                              save_bare_embargos,
                                              save_bare_retractions,
                                              save_bare_nodes,
                                              save_bare_system_tags,
                                              save_bare_tags, save_bare_users,
                                              set_node_foreign_keys_on_nodes,
                                              set_node_many_to_many_on_nodes,
                                              set_node_many_to_many_on_users,
                                              set_system_tag_many_to_many_on_users,
                                              set_tag_many_to_many_on_nodes,
                                              set_user_foreign_keys_on_nodes,
                                              set_user_foreign_keys_on_users,
                                              set_user_many_to_many_on_nodes,
                                              set_user_many_to_many_on_users, set_retraction_foreign_keys_on_nodes,
                                              set_embargo_foreign_keys_on_nodes, merge_duplicate_users,
                                              save_bare_institutions, save_bare_registrations, save_bare_collections)
from osf_models.scripts.verify_guids import main as verify_guids
from osf_models.scripts.verify_nodelogs import main as verify_nodelogs
from osf_models.scripts.verify_nodes import main as verify_nodes
from website.app import init_app


class Command(BaseCommand):
    help = 'Migrates data from tokumx to postgres'

    def handle(self, *args, **options):
        print('DEPRECATED -- Call individual mgmt commands')
        return
        print('Initializing Flask App...')
        init_app()
        start = datetime.now()

        load_guids()
        print('Loaded Guids in {} seconds...'.format((datetime.now() - start
                                                      ).total_seconds()))
        snap = datetime.now()
        load_blacklist_guids()
        print('Loaded Blacklist in {} seconds...'.format((datetime.now() - snap
                                                          ).total_seconds()))
        save_bare_nodes()
        save_bare_institutions()
        save_bare_registrations()
        save_bare_collections()
        merge_duplicate_users()
        save_bare_users()
        save_bare_tags()
        save_bare_system_tags()

        global modm_to_django
        modm_to_django = build_pk_caches()
        print('Cached {} MODM to django mappings...'.format(len(
            modm_to_django.keys())))

        save_bare_embargos()
        save_bare_retractions()
        print('\a\a\a\a\a\a\a\a\a\a\a\a')

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
        print('\a\a\a\a\a\a\a\a\a\a\a\a')

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
        print('\a\a\a\a\a\a\a\a\a\a\a\a')

        global modm_to_django
        modm_to_django = build_pk_caches()
        print('Cached {} MODM to django mappings...'.format(len(
            modm_to_django.keys())))

        # verify
        verify_guids()
        verify_nodes()
        print('\a\a\a\a\a\a\a\a\a\a\a\a')

        # nodelogs
        migrate_nodelogs()
        print('\a\a\a\a\a\a\a\a\a\a\a\a')

        # verify nodelogs
        verify_nodelogs()
        print('\a\a\a\a\a\a\a\a\a\a\a\a')

        print('Finished in {} seconds...'.format((datetime.now() - start
                                                  ).total_seconds()))
