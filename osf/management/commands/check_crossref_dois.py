from datetime import timedelta
import logging
import requests

import django
from django.core.management.base import BaseCommand
from django.utils import timezone
django.setup()

from framework import sentry
from framework.celery_tasks import app as celery_app
from osf.models import Guid, Preprint
from website import mails, settings


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

time_since_published = timedelta(days=settings.DAYS_CROSSREF_DOIS_MUST_BE_STUCK_BEFORE_EMAIL)

CHECK_DOIS_BATCH_SIZE = 20


def pop_slice(lis, n):
    tem = lis[:n]
    del lis[:n]
    return tem

def create_dois_locally():
    """
    This script creates identifiers for preprints which have pending DOI in local environment.
    """
    preprints_with_pending_doi = Preprint.objects.filter(
        preprint_doi_created__isnull=True,
        is_published=True
    )

    for preprint in preprints_with_pending_doi:
        client = preprint.get_doi_client()
        doi = client.build_doi(preprint=preprint) if client else None
        preprint.set_identifier_values(doi, save=True)

def check_crossref_dois(dry_run=True):
    """
    This script is to check for any DOI confirmation messages we may have missed during downtime and alert admins to any
    DOIs that have been pending for X number of days. It creates url to check with crossref if all our pending crossref
    DOIs are minted, then sets all identifiers which are confirmed minted.

    :param dry_run:
    :return:
    """

    preprints_with_pending_dois = Preprint.objects.filter(
        preprint_doi_created__isnull=True,
        is_published=True
    ).exclude(date_published__gt=timezone.now() - time_since_published)

    if not preprints_with_pending_dois.exists():
        return

    preprints = list(preprints_with_pending_dois)

    while preprints:
        preprint_batch = pop_slice(preprints, CHECK_DOIS_BATCH_SIZE)

        pending_dois = []
        for preprint in preprint_batch:
            doi_prefix = preprint.provider.doi_prefix
            if not doi_prefix:
                sentry.log_message(f'Preprint [_id={preprint._id}] has been skipped for CrossRef DOI Check '
                                   f'since the provider [_id={preprint.provider._id}] has invalid DOI Prefix '
                                   f'[doi_prefix={doi_prefix}]')
                continue
            pending_dois.append(f'doi:{settings.DOI_FORMAT.format(prefix=doi_prefix, guid=preprint._id)}')

        url = '{}works?filter={}'.format(settings.CROSSREF_JSON_API_URL, ','.join(pending_dois))

        try:
            resp = requests.get(url)
            resp.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            sentry.log_message(f'Could not contact crossref to check for DOIs, response returned with exception {exc}')
            continue

        preprints_response = resp.json()['message']['items']

        for preprint in preprints_response:
            preprint__id = preprint['DOI'].split('/')[-1]
            base_guid, version = Guid.split_guid(preprint__id)
            if not base_guid or not version:
                sentry.log_message(f'[Skipped] Preprint [_id={preprint__id}] returned by CrossRef API has invalid _id')
                continue
            pending_preprint = preprints_with_pending_dois.filter(
                versioned_guids__guid___id=base_guid,
                versioned_guids__version=version,
            ).first()
            if not pending_preprint:
                sentry.log_message(f'[Skipped] Preprint [_id={preprint__id}] returned by CrossRef API is not found.')
                continue
            if not dry_run:
                logger.debug(f'Set identifier for {pending_preprint._id}')
                pending_preprint.set_identifier_values(preprint['DOI'], save=True)
            else:
                logger.info(f'DRY RUN: Set identifier for {pending_preprint._id}')


def report_stuck_dois(dry_run=True):

    preprints_with_pending_dois = Preprint.objects.filter(preprint_doi_created__isnull=True,
                                                          is_published=True,
                                                          date_published__lt=timezone.now() - time_since_published)

    if preprints_with_pending_dois:
        guids = ', '.join(preprints_with_pending_dois.values_list('guids___id', flat=True))
        if not dry_run:
            mails.send_mail(
                to_addr=settings.OSF_SUPPORT_EMAIL,
                mail=mails.CROSSREF_DOIS_PENDING,
                pending_doi_count=preprints_with_pending_dois.count(),
                time_since_published=time_since_published.days,
                guids=guids,
            )
        else:
            logger.info('DRY RUN')

        logger.info(f'There were {preprints_with_pending_dois.count()} stuck registrations for CrossRef, email sent to help desk')


@celery_app.task(name='management.commands.check_crossref_dois')
def main(dry_run=False):
    check_crossref_dois(dry_run=dry_run)
    report_stuck_dois(dry_run=dry_run)


class Command(BaseCommand):
    help = '''Checks if we've missed any Crossref DOI confirmation emails. '''

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='Dry run',
        )

    # Management command handler
    def handle(self, *args, **options):
        dry_run = options.get('dry_run', True)
        main(dry_run=dry_run)
