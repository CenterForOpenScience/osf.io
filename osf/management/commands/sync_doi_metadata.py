#!/usr/bin/env python3
import time
import datetime
import logging

from django.core.management.base import BaseCommand
from datacite.errors import DataCiteServerError
from website.identifiers.clients.exceptions import CrossRefRateLimitError
from osf.models import Identifier

from framework.celery_tasks import app

logger = logging.getLogger(__name__)


RATE_LIMIT_RETRY_DELAY = 60 * 5


@app.task(name='osf.management.commands.sync_doi_metadata', max_retries=5, default_retry_delay=RATE_LIMIT_RETRY_DELAY)
def sync_identifier_doi(identifier_id, delay=0):
    identifier = Identifier.objects.get(id=identifier_id)

    def run_sync(delay_time):
        time.sleep(delay_time)
        identifier.referent.request_identifier_update('doi')
        identifier.save()
        logger.info(f'Doi update for {identifier.value} complete')

    try:
        run_sync(delay)
        return
    except CrossRefRateLimitError as err:
        logger.warning(f'Doi update for {identifier.value} failed because of rate limit: {err}')
    except DataCiteServerError as err:
        # the first param is status code, the second one is text
        # see create_identifier.metadata_post call in datacite.py
        status_code, text = err.args
        if status_code == 429:
            logger.warning(f'Doi update for {identifier.value} failed because of rate limit: {text}')
        else:
            logger.warning(f'Doi update for {identifier.value} failed. Error: {text}')
    except Exception as err:
        logger.warning(f'Doi update for {identifier.value} failed because of an unexpected error: {err}')

    run_sync(RATE_LIMIT_RETRY_DELAY)


def sync_doi_metadata(modified_date, batch_size=100, dry_run=True, sync_private=False, rate_limit=100):

    identifiers = Identifier.objects.filter(
        category='doi',
        deleted__isnull=True,
        modified__lte=modified_date,
        object_id__isnull=False,
    )
    if batch_size:
        identifiers = identifiers[:batch_size]
        rate_limit = batch_size if batch_size > rate_limit else rate_limit

    logger.info(f'{"[DRY RUN]: " if dry_run else ""}'
                f'{identifiers.count()} identifiers to mint')

    delay = 0
    for record_number, identifier in enumerate(identifiers, 1):
        if dry_run:
            logger.info(f'{"[DRY RUN]: " if dry_run else ""}'
                        f' doi minting for {identifier.value} started')
            continue

        # in order to not reach rate limits that CrossRef and DataCite have, we increase delay after each
        # rate_limit records by 5 minutes
        if not record_number % rate_limit:
            delay += RATE_LIMIT_RETRY_DELAY

        if (identifier.referent.is_public and not identifier.referent.deleted and not identifier.referent.is_retracted) or sync_private:
            sync_identifier_doi.apply_async(kwargs={'identifier_id': identifier.id, 'delay': delay})


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
        parser.add_argument(
            '--rate_limit',
            '-r',
            type=int,
            default=100,
            help='number of dois to update at the same time.',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run')
        sync_private = options.get('sync_private')
        batch_size = options.get('batch_size')
        modified_date = options.get('modified_date')
        rate_limit = options.get('rate_limit')
        sync_doi_metadata(modified_date, batch_size, dry_run=dry_run, sync_private=sync_private, rate_limit=rate_limit)
