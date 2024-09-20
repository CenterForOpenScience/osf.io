#!/usr/bin/env python3
import datetime
import logging

from django.core.management.base import BaseCommand
from osf.models import Identifier

from framework.celery_tasks import app

logger = logging.getLogger(__name__)


@app.task(name='osf.management.commands.sync_doi_metadata', max_retries=5, default_retry_delay=60)
def sync_identifier_doi(identifier_id):
    identifier = Identifier.objects.get(id=identifier_id)
    identifier.referent.request_identifier_update('doi')
    identifier.save()
    logger.info(f' doi update for {identifier.value} complete')


def sync_doi_metadata(modified_date, batch_size=100, dry_run=True, sync_private=False):

    identifiers = Identifier.objects.filter(
        category='doi',
        deleted__isnull=True,
        modified__lte=modified_date,
        object_id__isnull=False,
    )[:batch_size]
    logger.info(f'{"[DRY RUN]: " if dry_run else ""}'
                f'{identifiers.count()} identifiers to mint')

    for identifier in identifiers:
        if not dry_run:
            if (identifier.referent.is_public and not identifier.referent.deleted and not identifier.referent.is_retracted) or sync_private:
                sync_identifier_doi.apply_async(kwargs={'identifier_id': identifier.id})

        logger.info(f'{"[DRY RUN]: " if dry_run else ""}'
                    f' doi minting for {identifier.value} started')


class Command(BaseCommand):
    """ Adds updates all DOIs, will remove metadata for DOI bearing resources that have been withdrawn. """
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--dry_run',
            action='store_true',
            dest='dry_run',
        )
        parser.add_argument(
            '--sync_private',
            action='store_true',
            dest='sync_private',
        )
        parser.add_argument(
            '--batch_size',
            '-b',
            type=int,
            default=100,
            help='number of dois to update in this batch.',
        )
        parser.add_argument(
            '--modified_date',
            '-m',
            type=lambda s: datetime.datetime.strptime(s, '%Y-%m-%d %H:%M:%S.%f'),
            help='include all dois updated before this date.',
            required=True
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run')
        sync_private = options.get('sync_private')
        batch_size = options.get('batch_size')
        modified_date = options.get('modified_date')
        sync_doi_metadata(modified_date, batch_size, dry_run=dry_run, sync_private=sync_private)
