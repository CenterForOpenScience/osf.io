from __future__ import print_function
from datetime import datetime
from django.core.management import BaseCommand
from osf_models.scripts.migrate_nodes import save_bare_nodes, save_bare_institutions, save_bare_registrations, \
    save_bare_collections, merge_duplicate_users, save_bare_users, save_bare_tags, save_bare_system_tags, \
    build_pk_caches, save_bare_embargos, save_bare_retractions

from website.app import init_app
from osf_models.scripts.load_guids import main as load_guids
from osf_models.scripts.load_blacklist_guids import \
    main as load_blacklist_guids

class Command(BaseCommand):
    help = 'Migrates bare objects from tokumx to postgres'

    def handle(self, *args, **options):
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

        print('Finished in {} seconds...'.format((datetime.now() - start
                                                  ).total_seconds()))
