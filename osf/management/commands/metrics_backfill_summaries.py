"""osf/management/commands/metrics_backfill_summaries.py

usage:

  $ dc-manage metrics_backfill_summaries --which=$which_metric --source=$path_to_csv

where ``$which_metric`` is one of:

  file_summary
  download_count
  preprint_summary
  institution_summary
  user_summary
  node_summary

"""
import csv
import logging
import datetime

from django.core.management.base import BaseCommand
from osf.metrics import (
    DownloadCountReport,
    InstitutionSummaryReport,
    # NewUserDomainReport,
    NodeSummaryReport,
    OsfstorageFileCountReport,
    PreprintSummaryReport,
    # StorageAddonUsage,
    UserSummaryReport,
)


logger = logging.getLogger(__name__)


def main(source, which, dry_run=False, resume_from=None):
    if which not in SUMMARIES:
        logger.info(f'No such summary, {which}, exiting.')
        return

    if not source:
        logger.info('No path to source data file, exiting.')
        return

    summary_meta = SUMMARIES[which]

    logger.info('Kicking off...')
    with open(source) as csvfile:
        reader = csv.DictReader(csvfile)

        count = 0
        for row in reader:
            count += 1
            if resume_from is not None and count < resume_from:
                continue

            something_wonderful = summary_meta['mapper'](row)
            logger.info(f'{count}: transformed:({something_wonderful})')
            if not dry_run:
                summary_meta['class'].record(**something_wonderful)

    logger.info('All done!')
    if which == 'preprint_summary':
        logger.error(f'Unrecognized provider names: ({bogus_preprints})')


def _map_download_count(row):
    # date(keen.timestamp) => _source.report_date          # "2022-12-30",
    # keen.created_at      => _source.timestamp            # "2023-01-02T14:58:38.041721+00:00"
    # files.total          => _source.daily_file_downloads # 0,
    return {
        'report_date': _timestamp_to_date(row['keen.timestamp']),
        'timestamp': _timestamp_to_dt(row['keen.created_at']),
        'daily_file_downloads': int(row['files.total']),
    }

def _map_file_summary(row):
    # date(keen.timestamp)                                => _source.report_date         # "2022-12-30",
    # keen.created_at                                     => _source.timestamp           # "2023-01-02T14:59:04.397056+00:00"
    # osfstorage_files_including_quickfiles.total         => _source.files.total         # 12272,
    # osfstorage_files_including_quickfiles.public        => _source.files.public        # 126,
    # osfstorage_files_including_quickfiles.private       => _source.files.private       # 12146,
    # osfstorage_files_including_quickfiles.total_daily   => _source.files.total_daily   # 0,
    # osfstorage_files_including_quickfiles.public_daily  => _source.files.public_daily  # 0,
    # osfstorage_files_including_quickfiles.private_daily => _source.files.private_daily # 0
    return {
        'report_date': _timestamp_to_date(row['keen.timestamp']),
        'timestamp': _timestamp_to_dt(row['keen.created_at']),
        'files': {
            'total': int(row['osfstorage_files_including_quickfiles.total']),
            'public': int(row['osfstorage_files_including_quickfiles.public']),
            'private': int(row['osfstorage_files_including_quickfiles.private']),
            'total_daily': int(row['osfstorage_files_including_quickfiles.total_daily']),
            'public_daily': int(row['osfstorage_files_including_quickfiles.public_daily']),
            'private_daily': int(row['osfstorage_files_including_quickfiles.private_daily']),
        },
    }


def _map_institution_summary(row):
    # date(keen.timestamp) => _source.report_date # "2022-12-30",
    # keen.created         => _source.timestamp   # "2023-01-02T14:59:01.706319+00:00"
    # institution.id       => _source.institution_id # "okstate",
    # institution.name     => _source.institution_name # "Oklahoma State University [Test]",
    # ### => _source.users # {}
    # users.total       => _source.total       # 0,
    # users.total_daily => _source.total_daily # 0
    # ### => _source.nodes # {}
    # nodes.total         => _source.nodes.total": 0,
    # nodes.public        => _source.nodes.public": 0,
    # nodes.private       => _source.nodes.private": 0,
    # nodes.total_daily   => _source.nodes.total_daily": 0,
    # nodes.public_daily  => _source.nodes.public_daily": 0,
    # nodes.private_daily => _source.nodes.private_daily": 0
    # ### => _source.projects # {}
    # projects.total         => _source.projects.total": 0,
    # projects.public        => _source.projects.public": 0,
    # projects.private       => _source.projects.private": 0,
    # projects.total_daily   => _source.projects.total_daily": 0,
    # projects.public_daily  => _source.projects.public_daily": 0,
    # projects.private_daily => _source.projects.private_daily": 0
    # ### => _source.registered_nodes # {}
    # registered_nodes.total              => _source.registered_nodes.total": 0,
    # registered_nodes.public             => _source.registered_nodes.public": 0,
    # registered_nodes.embargoed          => _source.registered_nodes.embargoed": 0,
    # registered_nodes.embargoed_v2       => _source.registered_nodes.embargoed_v2": 0,
    # registered_nodes.total_daily        => _source.registered_nodes.total_daily": 0,
    # registered_nodes.public_daily       => _source.registered_nodes.public_daily": 0,
    # registered_nodes.embargoed_daily    => _source.registered_nodes.embargoed_daily": 0,
    # registered_nodes.embargoed_v2_daily => _source.registered_nodes.embargoed_v2_daily": 0
    # ### => _source.registered_projects # {}
    # registered_projects.total              => _source.registered_projects.total": 0,
    # registered_projects.public             => _source.registered_projects.public": 0,
    # registered_projects.embargoed          => _source.registered_projects.embargoed": 0,
    # registered_projects.embargoed_v2       => _source.registered_projects.embargoed_v2": 0,
    # registered_projects.total_daily        => _source.registered_projects.total_daily": 0,
    # registered_projects.public_daily       => _source.registered_projects.public_daily": 0,
    # registered_projects.embargoed_daily    => _source.registered_projects.embargoed_daily": 0,
    # registered_projects.embargoed_v2_daily => _source.registered_projects.embargoed_v2_daily": 0
    return {
        'report_date': _timestamp_to_date(row['keen.timestamp']),
        'timestamp': _timestamp_to_dt(row['keen.created_at']),
        'institution_id': row['institution.id'],
        'institution_name': row['institution.name'],
        'users': {
            'total': int(row['users.total']),
            'total_daily': int(row['users.total_daily'] or 0),
        },
        'nodes': {
            'total': int(row['nodes.total']),
            'public': int(row['nodes.public']),
            'private': int(row['nodes.private']),
            'total_daily': int(row['nodes.total_daily'] or 0),
            'public_daily': int(row['nodes.public_daily'] or 0),
            'private_daily': int(row['nodes.private_daily'] or 0),
        },
        'projects': {
            'total': int(row['projects.total']),
            'public': int(row['projects.public']),
            'private': int(row['projects.private']),
            'total_daily': int(row['projects.total_daily'] or 0),
            'public_daily': int(row['projects.public_daily'] or 0),
            'private_daily': int(row['projects.private_daily'] or 0),
        },
        'registered_nodes': {
            'total': int(row['registered_nodes.total']),
            'public': int(row['registered_nodes.public']),
            'embargoed': int(row['registered_nodes.embargoed']),
            'embargoed_v2': int(row['registered_nodes.embargoed_v2'] or 0),
            'total_daily': int(row['registered_nodes.total_daily'] or 0),
            'public_daily': int(row['registered_nodes.public_daily'] or 0),
            'embargoed_daily': int(row['registered_nodes.embargoed_daily'] or 0),
            'embargoed_v2_daily': int(row['registered_nodes.embargoed_v2_daily'] or 0),
        },
        'registered_projects': {
            'total': int(row['registered_projects.total']),
            'public': int(row['registered_projects.public']),
            'embargoed': int(row['registered_projects.embargoed']),
            'embargoed_v2': int(row['registered_projects.embargoed_v2'] or 0),
            'total_daily': int(row['registered_projects.total_daily'] or 0),
            'public_daily': int(row['registered_projects.public_daily'] or 0),
            'embargoed_daily': int(row['registered_projects.embargoed_daily'] or 0),
            'embargoed_v2_daily': int(row['registered_projects.embargoed_v2_daily'] or 0),
        },
    }

def _map_node_summary(row):
    # date(keen.timestamp) => _source.report_date # "2022-12-30",
    # keen.created_at      => _source.timestamp   # "2023-01-02T14:59:03.886999+00:00"
    # ### => _source.nodes # {}
    # nodes.total                      => _source.nodes.total # 58,
    # nodes.total_excluding_spam       => _source.nodes.total_excluding_spam # 58,
    # nodes.public                     => _source.nodes.public # 14,
    # nodes.private                    => _source.nodes.private # 44,
    # nodes.total_daily                => _source.nodes.total_daily # 0,
    # nodes.total_daily_excluding_spam => _source.nodes.total_daily_excluding_spam # 0,
    # nodes.public_daily               => _source.nodes.public_daily # 0,
    # nodes.private_daily              => _source.nodes.private_daily # 0
    # ### => _source.projects # {}
    # projects.total                       => _source.projects.total # 53,
    # projects.total_excluding_spam        => _source.projects.total_excluding_spam # 53,
    # projects.public                      => _source.projects.public # 14,
    # projects.private                     => _source.projects.private # 39,
    # projects.total_daily                 => _source.projects.total_daily # 0,
    # projects.total_daily_excluding_spam  => _source.projects.total_daily_excluding_spam # 0,
    # projects.public_daily                => _source.projects.public_daily # 0,
    # projects.private_daily               => _source.projects.private_daily # 0
    # ### => _source.registered_nodes # {}
    # registered_nodes.total              => _source.registered_nodes.total # 10,
    # registered_nodes.public             => _source.registered_nodes.public # 9,
    # registered_nodes.embargoed          => _source.registered_nodes.embargoed # 1,
    # registered_nodes.embargoed_v2       => _source.registered_nodes.embargoed_v2 # 0,
    # registered_nodes.withdrawn          => _source.registered_nodes.withdrawn # 0,
    # registered_nodes.total_daily        => _source.registered_nodes.total_daily # 0,
    # registered_nodes.public_daily       => _source.registered_nodes.public_daily # 0,
    # registered_nodes.embargoed_daily    => _source.registered_nodes.embargoed_daily # 0,
    # registered_nodes.embargoed_v2_daily => _source.registered_nodes.embargoed_v2_daily # 0,
    # registered_nodes.withdrawn_daily    => _source.registered_nodes.withdrawn_daily # 0
    # ### => _source.registered_projects # {}
    # registered_projects.total               => _source.registered_projects."total # 10,
    # registered_projects.public              => _source.registered_projects."public # 9,
    # registered_projects.embargoed           => _source.registered_projects."embargoed # 1,
    # registered_projects.embargoed_v2        => _source.registered_projects."embargoed_v2 # 0,
    # registered_projects.withdrawn           => _source.registered_projects."withdrawn # 0,
    # registered_projects.total_daily         => _source.registered_projects."total_daily # 0,
    # registered_projects.public_daily        => _source.registered_projects."public_daily # 0,
    # registered_projects.embargoed_daily     => _source.registered_projects."embargoed_daily # 0,
    # registered_projects.embargoed_v2_daily  => _source.registered_projects."embargoed_v2_daily # 0,
    # registered_projects.withdrawn_daily     => _source.registered_projects."withdrawn_daily # 0
    return {
        'report_date': _timestamp_to_date(row['keen.timestamp']),
        'timestamp': _timestamp_to_dt(row['keen.created_at']),
        'nodes': {
            'total': int(row['nodes.total'] or 0),
            'total_excluding_spam': int(row['nodes.total_excluding_spam'] or 0),
            'public': int(row['nodes.public'] or 0),
            'private': int(row['nodes.private'] or 0),
            'total_daily': int(row['nodes.total_daily'] or 0),
            'total_daily_excluding_spam': int(row['nodes.total_daily_excluding_spam'] or 0),
            'public_daily': int(row['nodes.public_daily'] or 0),
            'private_daily': int(row['nodes.private_daily'] or 0),
        },
        'projects': {
            'total': int(row['projects.total']),
            'total_excluding_spam': int(row['projects.total_excluding_spam'] or 0),
            'public': int(row['projects.public'] or 0),
            'private': int(row['projects.private'] or 0),
            'total_daily': int(row['projects.total_daily'] or 0),
            'total_daily_excluding_spam': int(row['projects.total_daily_excluding_spam'] or 0),
            'public_daily': int(row['projects.public_daily'] or 0),
            'private_daily': int(row['projects.private_daily'] or 0),
        },
        'registered_nodes': {
            'total': int(row['registered_nodes.total'] or 0),
            'public': int(row['registered_nodes.public'] or 0),
            'embargoed': int(row['registered_nodes.embargoed'] or 0),
            'embargoed_v2': int(row['registered_nodes.embargoed_v2'] or 0),
            'withdrawn': int(row['registered_nodes.withdrawn'] or 0),
            'total_daily': int(row['registered_nodes.total_daily'] or 0),
            'public_daily': int(row['registered_nodes.public_daily'] or 0),
            'embargoed_daily': int(row['registered_nodes.embargoed_daily'] or 0),
            'embargoed_v2_daily': int(row['registered_nodes.embargoed_v2_daily'] or 0),
            'withdrawn_daily': int(row['registered_nodes.withdrawn_daily'] or 0),
        },
        'registered_projects': {
            'total': int(row['registered_projects.total'] or 0),
            'public': int(row['registered_projects.public'] or 0),
            'embargoed': int(row['registered_projects.embargoed'] or 0),
            'embargoed_v2': int(row['registered_projects.embargoed_v2'] or 0),
            'withdrawn': int(row['registered_projects.withdrawn'] or 0),
            'total_daily': int(row['registered_projects.total_daily'] or 0),
            'public_daily': int(row['registered_projects.public_daily'] or 0),
            'embargoed_daily': int(row['registered_projects.embargoed_daily'] or 0),
            'embargoed_v2_daily': int(row['registered_projects.embargoed_v2_daily'] or 0),
            'withdrawn_daily': int(row['registered_projects.withdrawn_daily'] or 0),
        },
    }


preprint_name_map = {
    'AfricArXiv': 'africarxiv',
    'AgriXiv': 'agrixiv',
    'Arabixiv': 'arabixiv',
    'BioHackrXiv': 'biohackrxiv',
    'BITSS': 'metaarxiv',
    'BodoArXiv': 'bodoarxiv',
    'coppreprints': 'coppreprints',
    'EarthArXiv': 'eartharxiv',
    'EcoEvoRxiv': 'ecoevorxiv',
    'ECSarXiv': 'ecsarxiv',
    'EdArXiv': 'edarxiv',
    'engrXiv': 'engrxiv',
    'FocUS Archive': 'focusarchive',
    'Frenxiv': 'frenxiv',
    'INA-Rxiv': 'inarxiv',
    'IndiaRxiv': 'indiarxiv',
    'LawArXiv': 'lawarxiv',
    'LIS Scholarship Archive': 'lissa',
    'LiveData': 'livedata',
    'Research AZ': 'livedata',
    'MarXiv': 'marxiv',
    'MedArXiv': 'medarxiv',
    'MediArXiv': 'mediarxiv',
    'MetaArXiv': 'metaarxiv',
    'MindRxiv': 'mindrxiv',
    'NutriXiv': 'nutrixiv',
    'Open Science Framework': 'osf',
    'PaleorXiv': 'paleorxiv',
    'PsyArXiv': 'psyarxiv',
    'SocArXiv': 'socarxiv',
    'SportRxiv': 'sportrxiv',
    'Thesis Commons': 'thesiscommons',
    'Vulnerability Assessment Testing': 'vulnerabilityassessmenttesting',
}
preprint_long_names = list(preprint_name_map.keys())
preprint_short_names = list(preprint_name_map.values())
bogus_preprints = {}
def _map_preprint_summary(row):
    # date(keen.timestamp) => _source.report_date    # "2022-12-30",
    # keen.created_at      => _source.timestamp      # "2023-01-02T14:59:05.684642+00:00"
    # provider.name        => _source.provider_key   # "psyarxiv",
    # provider.total       => _source.preprint_count # 0,

    # normalize provider names: we used to store the formal name, now we store the short name
    provider_key = None
    provider_name = row['provider.name']
    if provider_name in preprint_short_names:
        provider_key = provider_name
    elif provider_name in preprint_long_names:
        provider_key = preprint_name_map[provider_name]
    else:
        logger.error(f'Unrecognized preprint provider name: ({provider_name})')
        if provider_name not in bogus_preprints:
            bogus_preprints[provider_name] = 0
        bogus_preprints[provider_name] += 1
        provider_key = provider_name  # oh well

    return {
        'report_date': _timestamp_to_date(row['keen.timestamp']),
        'timestamp': _timestamp_to_dt(row['keen.created_at']),
        'provider_key': provider_key,
        'preprint_count': int(row['provider.total']),
    }

def _map_user_summary(row):
    # date(keen.timestamp)                    => _source.report_date                      # "2023-01-03",
    # keen.created_at                         => _source.timestamp                        # "2023-01-04T13:47:34.216419+00:00"
    # status.active                           => _source.active                           # 7,
    # status.deactivated                      => _source.deactivated                      # 0,
    # status.merged                           => _source.merged                           # 0,
    # status.new_users_daily                  => _source.new_users_daily                  # 0,
    # status.new_users_with_institution_daily => _source.new_users_with_institution_daily # 0,
    # status.unconfirmed                      => _source.unconfirmed                      # 0,
    return {
        'report_date': _timestamp_to_date(row['keen.timestamp']),
        'timestamp': _timestamp_to_dt(row['keen.created_at']),
        'active': int(row['status.active']),
        'deactivated': int(row['status.deactivated'] or 0),
        'merged': int(row['status.merged'] or 0),
        'new_users_daily': int(row['status.new_users_daily'] or 0),
        'new_users_with_institution_daily': int(row['status.new_users_with_institution_daily'] or 0),
        'unconfirmed': int(row['status.unconfirmed'] or 0),
    }

SUMMARIES = {
    'download_count': {
        'mapper': _map_download_count,
        'class': DownloadCountReport,
    },
    'file_summary': {
        'mapper': _map_file_summary,
        'class': OsfstorageFileCountReport,
    },
    'institution_summary': {
        'mapper': _map_institution_summary,
        'class': InstitutionSummaryReport,
    },
    'node_summary': {
        'mapper': _map_node_summary,
        'class': NodeSummaryReport,
    },
    'preprint_summary': {
        'mapper': _map_preprint_summary,
        'class': PreprintSummaryReport,
    },
    'user_summary': {
        'mapper': _map_user_summary,
        'class': UserSummaryReport,
    },
}

def _timestamp_to_dt(timestamp):
    return datetime.datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%fZ')

def _timestamp_to_date(timestamp):
    dt_obj = _timestamp_to_dt(timestamp)
    return dt_obj.date()


def _dt_to_date(dt):
    dt_obj = datetime.datetime.strptime(dt, '%Y-%m-%dT%H:%M:%S.%fZ')
    return str(dt_obj.date())

class Command(BaseCommand):

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--source',
            type=str,
            help='source file path (csv format w/ header line)',
        )
        parser.add_argument(
            '--dry',
            dest='dry',
            action='store_true',
            help='Dry run'
        )
        parser.add_argument(
            '--which',
            type=str,
            help='which metric summary this data is for'
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
        which = options.get('which', None)
        resume_from = options.get('resume_from', None)
        main(source, which, dry_run, resume_from)
