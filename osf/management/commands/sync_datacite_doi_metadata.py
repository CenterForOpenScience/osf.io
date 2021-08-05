#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time

from django.core.management.base import BaseCommand
from osf.models import Registration, Identifier
import logging
from datacite.errors import DataCiteForbiddenError
from django.contrib.contenttypes.models import ContentType

logger = logging.getLogger(__name__)

def sync_datacite_doi_metadata(dry_run=True, batch_size=100):
    content_type = ContentType.objects.get_for_model(Registration)
    reg_ids = Identifier.objects.filter(category='doi', content_type=content_type, deleted__isnull=True).values_list(
        'object_id',
        flat=True
    )

    registrations = Registration.objects.exclude(
        deleted__isnull=False,
        is_public=False,
        moderation_state='withdrawn'
    ).exclude(  # Strangely we are required to call exclude two times for a list comp.
        id__in=reg_ids
    )[:batch_size]
    logger.info(f'{"[DRY RUN]: " if dry_run else ""}'
                f'{registrations.count()} registrations to mint')

    for registration in registrations:
        retries = 4
        for i in reversed(range(retries)):
            try:
                if not dry_run:
                    doi = registration.request_identifier('doi')['doi']
                    registration.set_identifier_value('doi', doi)
                    break
            except DataCiteForbiddenError as e:
                if i < 1:
                    raise e
                time.sleep(10)

        logger.info(f'{"[DRY RUN]: " if dry_run else ""}'
                    f' doi minting for {registration._id} complete')


class Command(BaseCommand):
    """Adds DOIs to all registrations"""
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
        )
        parser.add_argument(
            '--batch_size',
            '-b',
            type=int,
            default=0,
            help='number of dois to create.',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run')
        batch_size = options.get('batch_size')
        sync_datacite_doi_metadata(dry_run=dry_run, batch_size=batch_size)
