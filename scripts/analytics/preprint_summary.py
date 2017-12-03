import pytz

import logging
import requests
from dateutil.parser import parse
from datetime import datetime, timedelta

from website.app import init_app
from scripts.analytics.base import SummaryAnalytics

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

LOG_THRESHOLD = 11


class PreprintSummary(SummaryAnalytics):

    @property
    def collection_name(self):
        return 'preprint_summary'

    def get_events(self, date):
        super(PreprintSummary, self).get_events(date)
        from osf.models import PreprintProvider

        # Convert to a datetime at midnight for queries and the timestamp
        timestamp_datetime = datetime(date.year, date.month, date.day).replace(tzinfo=pytz.UTC)
        query_datetime = timestamp_datetime + timedelta(1)

        elastic_query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "match": {
                                "type": "preprint"
                            }
                        },
                        {
                            "match": {
                                "sources": None
                            }
                        }
                    ],
                    'filter': [
                        {
                            "range": {
                                "date": {
                                    "lte": "{}||/d".format(query_datetime.strftime('%Y-%m-%d'))
                                }
                            }
                        }
                    ]
                }
            }
        }

        counts = []
        for preprint_provider in PreprintProvider.objects.all():
            name = preprint_provider.name if preprint_provider.name != 'Open Science Framework' else 'OSF'
            elastic_query['query']['bool']['must'][1]['match']['sources'] = name
            resp = requests.post('https://share.osf.io/api/v2/search/creativeworks/_search', json=elastic_query).json()
            counts.append({
                'keen': {
                    'timestamp': timestamp_datetime.isoformat()
                },
                'provider': {
                    'name': preprint_provider.name,
                    'total': resp['hits']['total'],
                },
            })

        return counts


def get_class():
    return PreprintSummary


if __name__ == '__main__':
    init_app()

    preprint_summary = PreprintSummary()
    args = preprint_summary.parse_args()
    yesterday = args.yesterday
    if yesterday:
        date = (datetime.today() - timedelta(1)).date()
    else:
        date = parse(args.date).date() if args.date else None
    events = preprint_summary.get_events(date)
    preprint_summary.send_events(events)
