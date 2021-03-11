#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time

from django.core.management.base import BaseCommand
from osf.models import Registration, Identifier
import logging
from datacite.errors import DataCiteForbiddenError
from django.contrib.contenttypes.models import ContentType

logger = logging.getLogger(__name__)

def sync_datacite_doi_metadata(dry_run=True, retries=4):
    content_type = ContentType.objects.get_for_model(Registration)
    reg_ids = Identifier.objects.filter(category='doi', content_type=content_type, deleted__isnull=True).values_list(
        'object_id',
        flat=True
    )

    registrations = Registration.objects.exclude(id__in=reg_ids)
    logger.info(f'{registrations.count()} registrations to mint')
    for registration in registrations:
        if not dry_run:
            try:
                doi = registration.request_identifier('doi')['doi']
                registration.set_identifier_value('doi', doi)
            except DataCiteForbiddenError as e:
                # Just rate limiting, sleep and retry
                logger.info(f'retrying for {registration._id}, {retries} retries left')
                if retries < 1:
                    raise e
                retries -= 1
                time.sleep(10)
                sync_datacite_doi_metadata(dry_run, retries)
                break

        logger.info(f'doi minting for {registration._id} complete')


class Command(BaseCommand):
    """Adds DOIs to all registrations"""
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run')
        sync_datacite_doi_metadata(dry_run=dry_run)
