import datetime
import logging

from django.core.management.base import BaseCommand
from django.apps import apps
from tqdm import tqdm

from bulk_update.helper import bulk_update
from framework.celery_tasks import app as celery_app

logger = logging.getLogger(__name__)

def extract_file_info(file):
    """
    Extracts name and file_id from the nested "extras" dictionary.
    Pulling name from selectedFileName and the file_id from the viewUrl.

    Some weird data here...such as {u'selectedFileName': u'No file selected'}
    :returns dictionary {'file_name': <file_name>, 'file_id': <file__id>}
    if both exist, otherwise {}
    """
    if file:
        name = file.get('selectedFileName', '')
        # viewUrl is the only place the file id is accurate.  On a
        # registration, the other file ids in extra refer to the original
        # file on the node, not the file that was archived on the reg
        view_url = file.get('viewUrl', '')
        file__id = view_url.split('/')[5] if view_url else ''
        if name and file__id:
            return {
                'file_name': name,
                'file_id': file__id
            }
    return {}

def format_extra(extra):
    """
    Pulls file names, and file ids out of "extra"
    Note: "extra" is typically an array, but for some data, it's a dict

    :returns array of dictionaries, of format
    [{'file_name': <filename>, 'file_id': <file__id>}]
    """
    files = []
    if isinstance(extra, list):
        for file in extra:
            file_info = extract_file_info(file)
            files.append(file_info)
    else:
        file_info = extract_file_info(extra)
        if file_info:
            files.append(file_info)
    return files


def get_value_or_extra(nested_response, block_type, key, keys):
    """
    Sometimes the relevant information is stored under "extra" for files,
    otherwise, "value".

    :params, nested dictionary
    :block_type, string, current block type
    :key, particular key in question
    :keys, array of keys remaining to recurse through to find the user's answer
    :returns array (files or multi-response answers) or a string IF deepest level of nesting,
    otherwise, returns a dictionary to get the next level of nesting.
    """
    keyed_value = nested_response.get(key, '')

    # If we are on the most deeply nested key (no more keys left in array),
    # and the block type is "file-input", the information we want is
    # stored under extra
    if block_type == 'file-input' and not keys:
        extra = format_extra(keyed_value.get('extra', []))
        return extra
    else:
        value = keyed_value.get('value', '')
        return value

def get_nested_answer(nested_response, block_type, keys):
    """
    Recursively fetches the nested response in registered_meta.

    :params nested_response dictionary
    :params keys array, of nested question_ids: ["recommended-analysis", "specify", "question11c"]
    :returns array (files or multi-response answers) or a string
    """
    if isinstance(nested_response, dict):
        key = keys.pop(0)
        # Returns the value associated with the given key
        value = get_value_or_extra(nested_response, block_type, key, keys)
        return get_nested_answer(value, block_type, keys)
    else:
        # Once we've drilled down through the entire dictionary, our nested_response
        # should be an array or a string
        return nested_response

def extract_registration_responses(schema, registered_meta):
    """
    Extracts questions/nested registration_responses - makes use of schema block `registration_response_key`
    and block_type to pull out the nested registered_meta

    For example, if the registration_response_key = "description-methods.planned-sample.question7b",
    this will recurse through the registered_meta, looking for each key, starting with "description-methods",
    then "planned-sample", and finally "question7b", returning the most deeply nested value corresponding
    with the final key to flatten the dictionary.

    :returns dictionary, registration_responses, flattened dictionary with registration_response_keys
    top-level
    """
    registration_responses = {}
    registration_response_keys = schema.schema_blocks.filter(
        registration_response_key__isnull=False
    ).values(
        'registration_response_key',
        'block_type'
    )

    for registration_response_key_dict in registration_response_keys:
        key = registration_response_key_dict['registration_response_key']
        registration_responses[key] = get_nested_answer(
            registered_meta,
            registration_response_key_dict['block_type'],
            key.split('.')
        )
    return registration_responses

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

def get_schema(resource):
    """
    Fetches the RegistrationSchema from the resource

    :param resource: DraftRegistration or Registration
    :returns RegistrationSchema
    """
    if getattr(resource, 'registered_meta', None):
        # Registrations
        RegistrationSchema = apps.get_model('osf.RegistrationSchema')
        schema_id = resource.registered_meta.keys()[0] if resource.registered_meta.keys() else None
        return RegistrationSchema.objects.get(_id=schema_id) if schema_id else None
    else:
        # DraftRegistrations
        return resource.registration_schema

def get_registration_metadata(resource, schema=None):
    """
    Fetches the original registration responses
    :param resource: DraftRegistration or Registration
    :returns dictionary, registration_metadata
    """
    if getattr(resource, 'registered_meta', None):
        # Registration - registered_meta is under the schema key
        return resource.registered_meta.get(schema._id, {})
    # Draft Registration
    return resource.registration_metadata

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
        schema = get_schema(resource)
        registration_metadata = get_registration_metadata(resource, schema)

        resource.registration_responses = extract_registration_responses(
            schema,
            registration_metadata,
        )
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
