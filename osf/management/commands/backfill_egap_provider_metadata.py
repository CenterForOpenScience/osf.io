from __future__ import unicode_literals

from datetime import datetime as dt
import logging
import pytz

from django.core.management.base import BaseCommand
from django.db.models import Max
from osf.models import Registration

logger = logging.getLogger(__name__)

# Historical context:
# https://github.com/CenterForOpenScience/osf.io/blob/50467ce8f156cea162666df6587614a7e95d4859/website/project/metadata/egap-registration.json
# https://github.com/CenterForOpenScience/osf.io/blob/50467ce8f156cea162666df6587614a7e95d4859/scripts/EGAP/egap-registration-3.json
EGAP_ID_KEY = 'q3'
EGAP_PUBLICATION_DATE_KEY = 'q4'
LAST_RELEVANT_VERSION = 3

WITH_OFFSET_DATE_FORMAT = '%Y-%m-%d %H:%M:%S %z'
NO_OFFSET_DATE_FORMAT = '%m/%d/%Y - %H:%M'
# ALL "Timestamp of Original Registration" values *should* match one of
# the above formats, but I spotted this one at least once in the wild.
HYBRID_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

def _get_date_registered(timestamp_string):
    '''Try to parse the provided timestamp_string with all known formats.'''
    if not timestamp_string:
        return None

    registered_date = None
    for date_format in [WITH_OFFSET_DATE_FORMAT, NO_OFFSET_DATE_FORMAT, HYBRID_DATE_FORMAT]:
        try:
            registered_date = dt.strptime(timestamp_string, date_format)
        except ValueError:
            continue

    # Could not successfully parse the date field
    if registered_date is None:
        raise ValueError(
            f'Un-parseable "Timestamp of Original Registration" value: {timestamp_string}'
        )

    # Mimic behavior of import_EGAP script for consistency
    if not registered_date.tzinfo:
        registered_date = registered_date.replace(tzinfo=pytz.UTC)
    return registered_date

def backfill_egap_metadata(dry_run=False, batch_size=None):
    egap_registrations = Registration.objects.annotate(
        # "Max" is a stupid way to extract the schema_version because
        # registered_schema is implemented as ManyToMany instead of FK
        schema_version=Max('registered_schema__schema_version')
    ).filter(
        provider___id='egap',
        additional_metadata=None,  # JSON fields are weird
        schema_version__lte=LAST_RELEVANT_VERSION
    )
    if batch_size:
        egap_registrations = egap_registrations[:batch_size]
    count = egap_registrations.count()

    logger.info(
        f'Backfilling EGAP ID and registered_date for {count} registrations'
    )
    for registration in egap_registrations:
        egap_id = registration.registration_responses.get(EGAP_ID_KEY)
        if egap_id:
            logger.info(
                f'{"[DRY RUN]: " if dry_run else ""}'
                f'Copying EGAP Registration ID {egap_id} to additional_metadata '
                f'for Registration with GUID {registration._id}'
            )
            # Starting with None value for additional_metadata, so assign a new dict
            registration.additional_metadata = {'EGAP Registration ID': egap_id}

        egap_registration_date = _get_date_registered(
            registration.registration_responses.get(EGAP_PUBLICATION_DATE_KEY)
        )
        if egap_registration_date is not None:
            logger.info(
                f'{"[DRY RUN]: " if dry_run else ""}'
                'Copying Timestamp or Original Registration to registered_date for '
                f'Registration with GUID {registration._id}'
            )
            registration.registered_date = egap_registration_date

        if not dry_run:
            registration.save()
    return count

class Command(BaseCommand):
    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='Dry run',
        )

        parser.add_argument(
            '--batch_size',
            type=int,
            default=0
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run')
        batch_size = options.get('batch_size')
        backfill_egap_metadata(dry_run=dry_run, batch_size=batch_size)
