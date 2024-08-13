"""osf/management/commands/metrics_backfill_user_domains.py

Usage:

  $ dc-manage metrics_backfill_user_domains --source=$path_to_csv
  $ dc-manage metrics_backfill_user_domains --source=$path_to_csv --dry  # dry run
  $ dc-manage metrics_backfill_user_domains --source=$path_to_csv --resume-from 1264  # start from record 1264


"""
import csv
import logging
import datetime

from django.core.management.base import BaseCommand
from osf.metrics import NewUserDomainReport

logger = logging.getLogger(__name__)

def main(source, dry_run=False, resume_from=None):
    if not source:
        logger.info('No source file detected, exiting.')
        return

    # new user domains report is weird, b/c old data needs to be aggregated by date & domain

    count = 0
    reader = csv.DictReader(source)
    tally = {}
    this_year = None
    for row in reader:
        count += 1
        if resume_from is not None and count < resume_from:
            continue

        logger.info(f'count:({count}) this_year:({this_year})')

        event_ts = _timestamp_to_dt(row['keen.timestamp'])
        event_date = event_ts.date()
        event_date_str = str(event_date)

        if this_year is None:
            logger.info('  >>> setting new year')
            this_year = event_date.year

        if this_year != event_date.year:
            # we've built up a year of data; commit and clear
            logger.info('   >>> year is up, committing data')
            _upload_data_and_purge(tally, dry_run)
            this_year = event_date.year
            logger.info('   >>> data committed, new year is:({}) and tally should be '
                        'empty:({})'.format(this_year, tally))

        if event_date_str not in tally:
            tally[event_date_str] = {
                'timestamp': event_ts,
                'report_date': event_date,
                'domains': {},
            }

        domain = row['domain']
        if domain not in tally[event_date_str]['domains']:
            tally[event_date_str]['domains'][domain] = 0
        tally[event_date_str]['domains'][domain] += 1

    _upload_data_and_purge(tally, dry_run)


def _upload_data_and_purge(tally, dry_run):
    for event_date_str, record in tally.items():
        for domain, count in record['domains'].items():

            # date(keen.timestamp) => _source.report_date    # "2022-12-30",
            # keen.created_at      => _source.timestamp      # "2023-01-02T14:59:05.684642+00:00"
            # domain               => _source.domain_name    # metrics.Keyword()
            # count_agg(domain)    => _source.new_user_count # metrics.Integer()

            something_wonderful = {
                'timestamp': record['timestamp'],
                'report_date': record['report_date'],
                'domain_name': domain,
                'new_user_count': count,
            }

            logger.info(f'    *** {event_date_str}::{domain}::{count}')
            logger.info('    *** {}::{}: something wonderful:({})'.format(event_date_str, domain,
                                                                          something_wonderful))

            if not dry_run:
                NewUserDomainReport.record(**something_wonderful)

    # purge tally
    tally.clear()


def _timestamp_to_dt(timestamp):
    return datetime.datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=datetime.UTC)

def _timestamp_to_date(timestamp):
    dt_obj = _timestamp_to_dt(timestamp)
    return str(dt_obj.date())


class Command(BaseCommand):

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--source',
            type=open,
            help='source file (csv format w/ header line)',
        )
        parser.add_argument(
            '--dry',
            dest='dry',
            action='store_true',
            help='Dry run'
        )
        parser.add_argument(
            '--resume-from',
            dest='resume_from',
            type=int,
            help='start from which record',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry', None)
        source = options.get('source', None)
        resume_from = options.get('resume_from', None)
        main(source, dry_run, resume_from)
