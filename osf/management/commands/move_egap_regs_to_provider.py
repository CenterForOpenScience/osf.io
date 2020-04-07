from __future__ import unicode_literals
import logging

from django.core.management.base import BaseCommand

from scripts import utils as script_utils

logger = logging.getLogger(__name__)

from osf.models import (
    RegistrationProvider,
    RegistrationSchema,
    Registration
)
from django.conf import settings

def main(dry_run):
    epag_provider = RegistrationProvider.objects.get(name=settings.EGAP_PROVIDER_NAME)

    egap_schema = RegistrationSchema.objects.filter(
        name='EGAP Registration'
    ).order_by(
        '-schema_version'
    )[0]

    egap_regs = Registration.objects.filter(registered_schema=egap_schema.id, provider___id='osf')

    if dry_run:
        logger.info(f'[DRY RUN] {egap_regs.count()} updated to {epag_provider} with id {epag_provider.id}')
    else:
        egap_regs.update(provider_id=epag_provider.id)


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
        if not dry_run:
            script_utils.add_file_logger(logger, __file__)

        main(dry_run=dry_run)
