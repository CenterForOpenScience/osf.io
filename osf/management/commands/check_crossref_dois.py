import logging
import requests

from datetime import timedelta

from framework.celery_tasks import app as celery_app
from website import settings
from website import mails
from django.utils import timezone
from django.core.management.base import BaseCommand

import django
django.setup()

from osf.models import Preprint

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def check_crossref_dois(dry_run=True):
    """
    This script is to check for any DOI confirmation messages we may have missed during downtime and alert admins to any
    DOIs that have been pending for X number of days.
    :param dry_run:
    :return:
    """
    # Create one enormous url to check if all our pending crossref DOIs are good, then set all identifers
    preprints_with_pending_dois = Preprint.objects.filter(preprint_doi_created__isnull=True,
                                                      is_published=True)

    if not preprints_with_pending_dois:
        return

    pending_dois = []

    for preprint in preprints_with_pending_dois:
        prefix = preprint.provider.doi_prefix
        pending_dois.append('doi:{}'.format(settings.DOI_FORMAT.format(prefix=prefix, guid=preprint._id)))

    url = '{}works?filter={}'.format(settings.CROSSREF_JSON_API_URL, ','.join(pending_dois))

    try:
        resp = requests.get(url)
        resp.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        logger.error('Could not contact crossref to check for DOIs, response returned with exception {}'.format(exc))
        raise exc

    preprints = resp.json()['message']['items']

    for preprint in preprints:
        guid = preprint['DOI'].split('/')[-1]
        pending_preprint = preprints_with_pending_dois.get(guids___id=guid)
        if not dry_run:
            pending_preprint.set_identifier_values(preprint['DOI'], save=True)
        else:
            logger.info('DRY RUN')


def report_stuck_dois(dry_run=True):
    time_since_published = timedelta(days=settings.DAYS_CROSSREF_DOIS_MUST_BE_STUCK_BEFORE_EMAIL)

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

        logger.info('There were {} stuck registrations for CrossRef, email sent to help desk'.format(preprints_with_pending_dois.count()))


@celery_app.task(name='management.commands.check_crossref_dois')
def main(dry_run=False):
    check_crossref_dois(dry_run=dry_run)
    report_stuck_dois(dry_run=dry_run)


class Command(BaseCommand):
    help = '''Checks if we've missed any Crossref DOI confirmation emails. '''

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='Dry run',
        )

    # Management command handler
    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        main(dry_run=dry_run)
