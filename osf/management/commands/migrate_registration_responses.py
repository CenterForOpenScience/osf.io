import datetime
import logging

from django.core.management.base import BaseCommand
from django.apps import apps
from tqdm import tqdm

from bulk_update.helper import bulk_update
from framework.celery_tasks import app as celery_app

logger = logging.getLogger(__name__)

def migrate_registrations(dry_run, rows='all'):
    """
    Loops through registrations whose registration_responses have not been migrated,
    and pulls this information from the "registered_meta" and flattens it, with
    keys being the "registration_response_key"s and values being the most deeply
    nested user response in registered_meta
    """
    AbstractNode = apps.get_model('osf.AbstractNode')
    registrations = AbstractNode.objects.filter(
        registration_responses_migrated=False,
        type='osf.registration'
    )
    regs_count = len(registrations)
    logger.info('{} registrations need migrating'.format(regs_count))

    migrate_responses(registrations, regs_count, dry_run, rows)

    registrations_remaining = AbstractNode.objects.filter(
        registration_responses_migrated=False,
        type='osf.registration'
    )
    logger.info('{} registrations remaining'.format(registrations_remaining.count()))

def migrate_draft_registrations(dry_run, rows='all'):
    """
    Populates a subset of draft_registration.registration_responses, and corresponding
    draft_registration.registration_responses_migrated.
    :params dry_run
    :params rows - if rows=0, all
    """
    DraftRegistration = apps.get_model('osf.DraftRegistration')
    draft_registrations = DraftRegistration.objects.filter(
        registration_responses_migrated=False
    )
    drafts_count = len(draft_registrations)
    logger.info('{} draft registrations need migrating'.format(drafts_count))

    migrate_responses(draft_registrations, drafts_count, dry_run, rows)

    draft_registrations_remaining = DraftRegistration.objects.filter(
        registration_responses_migrated=False
    )
    logger.info('{} draft registration remaining'.format(draft_registrations_remaining.count()))

def migrate_responses(resources, resources_count, dry_run=False, rows='all'):
    """
    DRY method to be used to migrate both DraftRegistration.registration_responses
    and Registration.registration_responses.
    """
    if rows == 'all' or resources_count <= rows:
        rows = resources_count

    resources = resources[:rows]
    logger.info('Migrating {} registration_responses.'.format(rows))
    to_save = []
    progress_bar = tqdm(total=rows)
    for resource in resources:
        resource.registration_responses = resource.flatten_registration_metadata()
        resource.registration_responses_migrated = True
        to_save.append(resource)
        progress_bar.update()
    progress_bar.close()

    if not dry_run:
        bulk_update(resources, update_fields=['registration_responses', 'registration_responses_migrated'])


@celery_app.task(name='management.commands.migrate_registration_responses')
def migrate_registration_responses(dry_run=False, rows=5000):
    script_start_time = datetime.datetime.now()
    logger.info('Script started time: {}'.format(script_start_time))

    migrate_draft_registrations(dry_run, rows)
    migrate_registrations(dry_run, rows)

    script_finish_time = datetime.datetime.now()
    logger.info('Script finished time: {}'.format(script_finish_time))
    logger.info('Run time {}'.format(script_finish_time - script_start_time))


class Command(BaseCommand):
    help = """ Incrementally migrates DraftRegistration.registration_metadata
    -> DraftRegistration.registration_responses, and Registration.registered_meta
    -> Registration.registered_responses. registration_responses is a flattened version
    of registration_metadata/registered_meta.

    This will need to be run multiple times to migrate all records on prod.
     """

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry_run',
            type=bool,
            default=False,
            help='Run queries but do not write files',
        )
        parser.add_argument(
            '--rows',
            default=5000,
            help='How many rows to process during this run',
        )

    # Management command handler
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        rows = options['rows']
        if dry_run:
            logger.info('DRY RUN')

        migrate_registration_responses(dry_run, rows)
