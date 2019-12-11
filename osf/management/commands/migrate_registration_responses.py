import datetime
import logging

from django.core.management.base import BaseCommand
from django.apps import apps
from tqdm import tqdm

from bulk_update.helper import bulk_update
from framework.celery_tasks import app as celery_app
from framework import sentry

from osf.exceptions import SchemaBlockConversionError
from osf.utils.registrations import flatten_registration_metadata

logger = logging.getLogger(__name__)

# because Registrations and DraftRegistrations are different
def get_nested_responses(registration_or_draft, schema_id):
    nested_responses = getattr(
        registration_or_draft,
        'registration_metadata',
        None,
    )
    if nested_responses is None:
        registered_meta = registration_or_draft.registered_meta or {}
        nested_responses = registered_meta.get(schema_id, None)
    return nested_responses

# because Registrations and DraftRegistrations are different
def get_registration_schema(registration_or_draft):
    schema = getattr(registration_or_draft, 'registration_schema', None)
    if schema is None:
        schema = registration_or_draft.registered_schema.first()
    return schema

def migrate_registrations(dry_run, rows='all', AbstractNodeModel=None):
    """
    Loops through registrations whose registration_responses have not been migrated,
    and pulls this information from the "registered_meta" and flattens it, with
    keys being the "registration_response_key"s and values being the most deeply
    nested user response in registered_meta
    """
    if AbstractNodeModel is None:
        AbstractNodeModel = apps.get_model('osf', 'abstractnode')

    registrations = AbstractNodeModel.objects.filter(
        type='osf.registration',
    ).exclude(
        registration_responses_migrated=True,
    )
    return migrate_responses(registrations, 'registrations', dry_run, rows)

def migrate_draft_registrations(dry_run, rows='all', DraftRegistrationModel=None):
    """
    Populates a subset of draft_registration.registration_responses, and corresponding
    draft_registration.registration_responses_migrated.
    :params dry_run
    :params rows
    """
    if DraftRegistrationModel is None:
        DraftRegistrationModel = apps.get_model('osf', 'draftregistration')

    draft_registrations = DraftRegistrationModel.objects.exclude(
        registration_responses_migrated=True
    )
    return migrate_responses(draft_registrations, 'draft registrations', dry_run, rows)

def migrate_responses(resources, resource_name, dry_run=False, rows='all'):
    """
    DRY method to be used to migrate both DraftRegistration.registration_responses
    and Registration.registration_responses.
    """
    progress_bar = None
    if rows == 'all':
        logger.info('Migrating all {}.'.format(resource_name))
    else:
        resources = resources[:rows]
        logger.info('Migrating up to {} {}.'.format(rows, resource_name))
        progress_bar = tqdm(total=rows)

    successes_to_save = []
    errors_to_save = []
    for resource in resources:
        try:
            schema = get_registration_schema(resource)
            resource.registration_responses = flatten_registration_metadata(
                schema,
                get_nested_responses(resource, schema._id),
            )
            resource.registration_responses_migrated = True
            successes_to_save.append(resource)
        except SchemaBlockConversionError as e:
            resource.registration_responses_migrated = False
            errors_to_save.append(resource)
            logger.error('Unexpected/invalid nested data in resource: {} with error {}'.format(resource, e))
        if progress_bar:
            progress_bar.update()

    if progress_bar:
        progress_bar.close()

    success_count = len(successes_to_save)
    error_count = len(errors_to_save)
    total_count = success_count + error_count

    if total_count == 0:
        logger.info('No {} left to migrate.'.format(resource_name))
        return total_count

    logger.info('Successfully migrated {} out of {} {}.'.format(success_count, total_count, resource_name))
    if error_count:
        logger.warn('Encountered errors on {} out of {} {}.'.format(error_count, total_count, resource_name))
        if not success_count:
            sentry.log_message('`migrate_registration_responses` has only errors left ({} errors)'.format(error_count))

    if dry_run:
        logger.info('DRY RUN; discarding changes.')
    else:
        logger.info('Saving changes...')
        bulk_update(successes_to_save, update_fields=['registration_responses', 'registration_responses_migrated'])
        bulk_update(errors_to_save, update_fields=['registration_responses_migrated'])

    return total_count


@celery_app.task(name='management.commands.migrate_registration_responses')
def migrate_registration_responses(dry_run=False, rows=5000):
    script_start_time = datetime.datetime.now()
    logger.info('Script started time: {}'.format(script_start_time))

    draft_count = migrate_draft_registrations(dry_run, rows)
    registration_count = migrate_registrations(dry_run, rows)

    if draft_count == 0 and registration_count == 0:
        logger.info('Migration complete! No more drafts or registrations need migrating.')
        sentry.log_message('`migrate_registration_responses` command found nothing to migrate!')

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
            type=int,
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
