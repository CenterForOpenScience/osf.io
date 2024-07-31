"""osf/management/commands/poke_metrics_timespan_queries.py
"""
import logging
import random
import datetime

from django.core.management.base import BaseCommand
from osf.metrics import CountedAuthUsage


logger = logging.getLogger(__name__)

TIME_FILTERS = (
    {'gte': 'now/d-150d'},
    {'gte': '2021-11-28T23:00:00.000Z', 'lte': '2023-01-16T00:00:00.000Z'},
)

PLATFORM_IRI = 'http://localhost:9201/'

ITEM_GUID = 'foo'


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=100,
            help='number of fake pageviews to generate',
        )
        parser.add_argument(
            '--seconds_back',
            type=int,
            default=60 * 60 * 24 * 14,  # up to two weeks back
            help='max age in seconds of random event',
        )

    def handle(self, *args, **options):
        self._generate_random_countedusage(options.get('count'), options.get('seconds_back'))

        results = [
            self._run_date_query(time_filter)
            for time_filter in TIME_FILTERS
        ]

        self._print_line(
            (str(f) for f in TIME_FILTERS),
            label='timefilter:',
        )

        date_keys = {
            k
            for r in results
            for k in r
        }
        for date_key in sorted(date_keys):
            self._print_line(
                (r.get(date_key, 0) for r in results),
                label=str(date_key),
            )

    def _print_line(self, lineitems, label=''):
        print('\t'.join((label, *map(str, lineitems))))

    def _generate_random_countedusage(self, n, max_age):
        now = datetime.datetime.now(tz=datetime.UTC)
        for _ in range(n):
            seconds_back = random.randint(0, max_age)
            timestamp_time = now - datetime.timedelta(seconds=seconds_back)
            CountedAuthUsage.record(
                platform_iri=PLATFORM_IRI,
                timestamp=timestamp_time,
                item_guid=ITEM_GUID,
                session_id='freshen by key',
                user_is_authenticated=bool(random.randint(0, 1)),
            )

    def _run_date_query(self, time_range_filter):
        result = self._run_query({
            'query': {
                'bool': {
                    'filter': {
                        'range': {
                            'timestamp': time_range_filter,
                        },
                    },
                },
            },
            'aggs': {
                'by-date': {
                    'date_histogram': {
                        'field': 'timestamp',
                        'interval': 'day',
                    },
                },
                'max-timestamp': {
                    'max': {'field': 'timestamp'},
                },
                'min-timestamp': {
                    'min': {'field': 'timestamp'},
                },
            },
        })
        return {
            'min': result.aggs['min-timestamp'].value_as_string,
            'max': result.aggs['max-timestamp'].value_as_string,
            **{
                str(bucket.key.date()): bucket.doc_count
                for bucket in result.aggs['by-date']
            },
        }

    def _run_query(self, query_dict):
        analytics_search = CountedAuthUsage.search().update_from_dict(query_dict)
        return analytics_search.execute()
