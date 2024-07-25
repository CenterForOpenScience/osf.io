"""osf/management/commands/metrics_backfill_pageviews.py

Usage:

  $ dc-manage metrics_backfill_pageviews --source=$path_to_csv
  $ dc-manage metrics_backfill_pageviews --source=$path_to_csv --dry  # dry run
  $ dc-manage metrics_backfill_pageviews --source=$path_to_csv --resume-from 1264  # start from record 1264


"""
import csv
import logging
import datetime

from django.core.management.base import BaseCommand
from osf.metrics import CountedAuthUsage
from osf.models import Guid

logger = logging.getLogger(__name__)

def main(source, dry_run=False, resume_from=None):
    if not source:
        logger.info('No source file detected, exiting.')
        return

    # keen.timestamp                        => _source.timestamp                    # "2023-01-19T04:06:45.675432+00:00",
    # page.info.protocol + page.info.domain => _source.platform_iri                 # "http://localhost:5000/",
    # visitor.session                       => _source.session_id                   # "fcae918a3b6a19641bd0087f84083f0d57982d8c93ab821c405561d1b5c7b305",
    # user.id                               => _source.user_is_authenticated        # true,
    # page.url                              => _source.pageview_info.page_url       # "http://localhost:5000/myprojects/",
    # page.title                            => _source.pageview_info.page_title     # "OSF | My Projects",
    # referrer.url                          => _source.pageview_info.referer_url    # "http://localhost:5000/csab4/analytics",
    # page.meta.routeName                   => _source.pageview_info.route_name     # "OsfWebRenderer.my_projects",
    # time.utc.hour_of_day                  => _source.pageview_info.hour_of_day    # 4,
    # page.info.path                        => _source.pageview_info.page_path      # "/myprojects",
    # referrer.info.domain                  => _source.pageview_info.referer_domain # "localhost:5000"
    # page.meta.public                      => _source.item_public # true,
    # node.id                               => _source.item_guid   # "ry7dn",

    # ??? => _source.provider_id # "osf",
    # ??? => _source.item_type   # "node"
    # ??? => _source.surrounding_guids = # [parent_guids?]
    # ??? => _source.action_labels                # ["web"]

    count = 0
    reader = csv.DictReader(source)
    for row in reader:
        if not row['page.url'].startswith('https://staging.osf.io'):
            continue

        count += 1
        if resume_from is not None and count < resume_from:
            continue

        something_wonderful = {
            'timestamp': _timestamp_to_dt(row['keen.timestamp']),
            'platform_iri': row['page.info.protocol'] + '://' + row['page.info.domain'],
            'session_id': row['visitor.session'],
            'user_is_authenticated': row['user.id'] is not None,
            'item_guid': row['node.id'],
            'item_public': row['page.meta.public'] or row['page.meta.pubic'],  # unfortunate misspelling
            'pageview_info': {
                'hour_of_day': row['time.utc.hour_of_day'],
                'page_path': row['page.info.path'],
                'page_title': row['page.title'],
                'page_url': row['page.url'],
                'referer_url': row['referrer.url'],
                'referer_domain': row['referrer.info.domain'],
                'route_name': row['page.meta.routeName'],
            },
        }

        db_info = annotate_from_db(row)
        if db_info:
            something_wonderful.update(db_info)
        populate_action_labels(something_wonderful, row)

        logger.info(f'*** {count}: something wonderful:({something_wonderful})')

        if not dry_run:
            CountedAuthUsage.record(**something_wonderful)

def populate_action_labels(something_wonderful, row):
    labels = ['web']

    if row['page.info.path']:
        path_parts = row['page.info.path'].split('/')
        if len(path_parts) == 1 and path_parts[0] not in ('myprojects', 'goodbye', 'login'):
            labels.append('view')
        elif path_parts[1] in ('wiki'):
            labels.append('view')

    if row['page.meta.routeName']:
        route_name = row['page.meta.routeName']
        if 'search' in route_name:
            labels.append('search')

    something_wonderful['action_labels'] = labels

guid_cache = {}
# this may be done by CountedAuthUsage._fill_osfguid_info
def annotate_from_db(row):
    item_guid = row['node.id']
    if not item_guid:
        return

    if not guid_cache.get(item_guid, None):
        guid_info = {}
        guid_instance = Guid.load(item_guid)

        if guid_instance and guid_instance.referent:
            guid_info = _fill_osfguid_info(guid_instance.referent)
        guid_cache[item_guid] = guid_info

    return guid_cache[item_guid]

# from CountedAuthUsage
def _fill_osfguid_info(guid_referent):
    guid_info = {}
    guid_info['item_public'] = _get_ispublic(guid_referent)
    guid_info['item_type'] = type(guid_referent).__name__.lower()
    guid_info['surrounding_guids'] = _get_surrounding_guids(guid_referent)
    guid_info['provider_id'] = _get_provider_id(guid_referent)
    return guid_info

def _get_ispublic(guid_referent):
    # if it quacks like BaseFileNode, look at .target instead
    maybe_public = getattr(guid_referent, 'target', None) or guid_referent
    if hasattr(maybe_public, 'verified_publishable'):
        return maybe_public.verified_publishable        # quacks like Preprint
    return getattr(maybe_public, 'is_public', None)     # quacks like AbstractNode

def _get_provider_id(guid_referent):
    provider = getattr(guid_referent, 'provider', None)
    if isinstance(provider, str):
        return provider         # quacks like BaseFileNode
    elif provider:
        return provider._id     # quacks like Registration, Preprint, Collection
    return 'osf'                # quacks like Node, Comment, WikiPage

def _get_immediate_wrapper(guid_referent):
    if hasattr(guid_referent, 'verified_publishable'):
        return None                                     # quacks like Preprint
    return (
        getattr(guid_referent, 'parent_node', None)     # quacks like AbstractNode
        or getattr(guid_referent, 'node', None)         # quacks like WikiPage, Comment
        or getattr(guid_referent, 'target', None)       # quacks like BaseFileNode
    )

def _get_surrounding_guids(guid_referent):
    """get all the parent/owner/surrounding guids for the given guid_referent

    @param guid_referent: instance of a model that has GuidMixin
    @returns list of str

    For AbstractNode, goes up the node hierarchy up to the root.
    For WikiPage or BaseFileNode, grab the node it belongs to and
    follow the node hierarchy from there.
    """
    surrounding_guids = []
    current_referent = guid_referent
    while current_referent:
        next_referent = _get_immediate_wrapper(current_referent)
        if next_referent:
            surrounding_guids.append(next_referent._id)
        current_referent = next_referent
    return surrounding_guids

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
