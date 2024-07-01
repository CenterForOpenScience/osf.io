from datetime import datetime
from functools import lru_cache

from django.core.management.base import BaseCommand
from django.db import transaction

from osf.models import Registration, RegistrationSchema
from website.settings import DOMAIN

'''
This management command fixes an accidentally hard-coded domain of "https://staging.osf.io/"
for all file responses on registrations as part of the osf.io 22.04.0 release.
'''


# 9 p.m. April 6, 2022, EDT; time of 22.04 release
SINCE_FORMAT = '%d-%m-%Y %H:%M %z'
RELEASE_TIME = '7-4-2022 01:00 +0000'
BAD_DOMAIN = 'https://staging.osf.io/'


@lru_cache(maxsize=128)
def get_schema_file_input_qids(schema_id):
    return set(
        RegistrationSchema.objects.get(id=schema_id).schema_blocks.filter(
            block_type='file-input'
        ).values_list(
            'registration_response_key',
            flat=True
        )
    )

def fix_registration_response_file_links(registration):
    schema = registration.registration_schema
    file_input_qids = get_schema_file_input_qids(schema.id)
    # Fix the *initial* schema_response
    # Any updates to file-input responses since then would have fixed the file references already
    initial_response = registration.schema_responses.last()
    if not initial_response:
        return
    for block in initial_response.response_blocks.all():
        if block.schema_key in file_input_qids:
            # SchemaResponseBlocks have a default value of [] for file-input blocks;
            # can safely iterate
            for file_response in block.response:
                urls = file_response['file_urls']
                urls['html'] = urls['html'].replace(BAD_DOMAIN, DOMAIN)
                urls['download'] = urls['download'].replace(BAD_DOMAIN, DOMAIN)
            block.save()

    # Re-set registration_responses and registered_meta bssed on the *latest* schema_response,
    # which will have inherited these fixes if not already explicitly updated
    registration.registration_responses = registration.schema_responses.first().all_responses
    registration.registered_meta[schema._id] = registration.expand_registration_responses()
    registration.save()


@transaction.atomic
def fix_registration_file_domains(dry_run=False, since=None):
    modified_threshold = since or datetime.strptime(RELEASE_TIME, SINCE_FORMAT)
    # Check modified instead of registration date as some registrations were "fixed" during release
    impacted_registrations = Registration.objects.filter(modified__gte=modified_threshold)
    for registration in impacted_registrations:
        fix_registration_response_file_links(registration)

    if dry_run:
        raise RuntimeError('Dry run, transaction rolled back')


class Command(BaseCommand):
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='Dry run',
        )

        parser.add_argument(
            '--since',
            type=str,
            default=RELEASE_TIME,
            help='When were the earliest registrations impacted? Format is DD-MM-YYYY HH:MM Offset'
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run')
        since = datetime.strptime(options.get('since'), SINCE_FORMAT)
        fix_registration_file_domains(dry_run=dry_run, since=since)
