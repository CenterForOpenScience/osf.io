from __future__ import unicode_literals

from datetime import datetime as dt
import logging
import pytz

from django.core.management.base import BaseCommand
from osf.models import RegistrationProvider

logger = logging.getLogger(__name__)

# Historical context:
# https://github.com/CenterForOpenScience/osf.io/blob/50467ce8f156cea162666df6587614a7e95d4859/website/project/metadata/egap-registration.json
# https://github.com/CenterForOpenScience/osf.io/blob/50467ce8f156cea162666df6587614a7e95d4859/scripts/EGAP/egap-registration-3.json
EGAP_ID_KEY = 'q3'
EGAP_PUBLICATION_DATE_KEY = 'q4'
LAST_SUPPORTED_VERSION = 3


def main(dry_run):
    egap_registrations = RegistrationProvider.objects.get(_id='egap').registrations.filter(
        additional_metadata__is_null=True,
        registered_schema__schema_version__lte=LAST_SUPPORTED_VERSION
    )

    logger.info(
        f'Backfilling EGAP ID and registered_date for {egap_registrations.count()} registrations'
    )
    for registration in egap_registrations:
        egap_id = registration.registration_responses.get(EGAP_ID_KEY)
        if egap_id:
            logger.info(
                f'Copying EGAP Registration ID {egap_id} to additional_metadata '
                f'for Registration with ID {registration.id}'
            )
            # Starting with None value for additional_metadata, so assign a new dict
            registration.additional_metadatai = {'EGAP Registration ID': egap_id}

        # adapted from import_EGAP command
        egap_registration_date_string = registration.registration_responses.get(
            EGAP_PUBLICATION_DATE_KEY)
        if egap_registration_date_string:
            egap_registration_date = dt.strptime(
                egap_registration_date_string, '%m/%d/%Y - %H:%M'
            ).replace(tzinfo=pytz.UTC)
            logger.info(
                'Copying EGAP Registration timestamp to registered_date '
                f'for Registration with ID {registration.id}'
            )
            registration.registered_date = egap_registration_date

        if not dry_run:
            registration.save()

class Command(BaseCommand):
    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='Dry run',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        main(dry_run=dry_run)
