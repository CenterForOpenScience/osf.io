from __future__ import print_function

from datetime import datetime

from django.core.management import BaseCommand
from osf_models import models
from osf_models.scripts.load_blacklist_guids import \
    main as load_blacklist_guids
from osf_models.scripts.load_guids import main as load_guids
from osf_models.scripts.migrate_nodes import save_bare_nodes, save_bare_institutions, save_bare_registrations, \
    save_bare_collections, merge_duplicate_users, save_bare_users, save_bare_tags, save_bare_system_tags, \
    build_pk_caches, save_bare

from website.app import init_app
from website.archiver.model import ArchiveTarget, ArchiveJob
from website.conferences.model import Conference
from website.project.model import AlternativeCitation, Comment, MetaSchema
from website.project.sanctions import Embargo as MODMEmbargo, Retraction as MODMRetraction, RegistrationApproval, \
    Retraction, Embargo, DraftRegistrationApproval, EmbargoTerminationApproval


class Command(BaseCommand):
    help = 'Migrates bare objects from tokumx to postgres'

    def add_arguments(self, parser):
        parser.add_argument('--skip-blacklist', action='store_true', help='Skip blacklist guids')

    def handle(self, *args, **options):
        print('Initializing Flask App...')
        init_app()
        start = datetime.now()

        load_guids()
        print('Loaded Guids in {} seconds...'.format((datetime.now() - start
                                                      ).total_seconds()))
        if not options['skip_blacklist']:
            snap = datetime.now()
            load_blacklist_guids()
            print('Loaded Blacklist in {} seconds...'.format((datetime.now() - snap
                                                              ).total_seconds()))
        else:
            print('Skipping BlacklistGuids...')

        save_bare(ArchiveJob, models.ArchiveJob)
        save_bare(ArchiveTarget, models.ArchiveTarget)
        save_bare(AlternativeCitation, models.AlternativeCitation)
        save_bare(Comment, models.Comment)
        save_bare(Conference, models.Conference)
        save_bare_institutions()
        save_bare(MetaSchema, models.MetaSchema)
        save_bare_nodes()
        save_bare_collections()
        save_bare_registrations()
        save_bare(Embargo, models.Embargo)
        save_bare(Retraction, models.Retraction)
        save_bare(RegistrationApproval, models.RegistrationApproval)
        save_bare(DraftRegistrationApproval, models.DraftRegistrationApproval)
        save_bare(EmbargoTerminationApproval, models.EmbargoTerminationApproval)
        save_bare_tags()
        save_bare_system_tags()
        merge_duplicate_users()
        save_bare_users()

        global modm_to_django
        modm_to_django = build_pk_caches()
        print('Cached {} MODM to django mappings...'.format(len(
            modm_to_django.keys())))


        print('Finished in {} seconds...'.format((datetime.now() - start
                                                  ).total_seconds()))
