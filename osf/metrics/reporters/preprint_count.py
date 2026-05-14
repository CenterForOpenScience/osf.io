import logging
import requests

from website import settings
from osf.metrics.es8_metrics import DailyPreprintSummaryReportEs8
from osf.metrics.utils import cycle_coverage_date
from ._base import DailyReporter

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

LOG_THRESHOLD = 11

def get_elastic_query(date, provider):
    return {
        'query': {
            'bool': {
                'must': [
                    {
                        'match': {
                            'type': 'preprint'
                        }
                    },
                    {
                        'match': {
                            'sources': provider.share_source or provider.name,
                        }
                    }
                ],
                'filter': [
                    {
                        'range': {
                            'date': {
                                'lte': '{}||/d'.format(date.strftime('%Y-%m-%d'))
                            }
                        }
                    }
                ]
            }
        }
    }


class PreprintCountReporter(DailyReporter):
    def report(self, date):
        from osf.models import PreprintProvider

        for preprint_provider in PreprintProvider.objects.all():
            elastic_query = get_elastic_query(date, preprint_provider)
            resp = requests.post(f'{settings.SHARE_URL}api/v2/search/creativeworks/_search', json=elastic_query).json()

            yield DailyPreprintSummaryReportEs8(
                cycle_coverage=cycle_coverage_date(date),
                provider_key=preprint_provider._id,
                preprint_count=resp['hits']['total'],
            )
