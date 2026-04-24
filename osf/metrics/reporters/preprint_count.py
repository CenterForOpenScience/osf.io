import logging
import requests

from osf.metrics import PreprintSummaryReport
from website import settings
from ._base import DailyReporter
from osf.metrics.es8_metrics import PreprintSummaryReportEs8

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

        reports = []
        for preprint_provider in PreprintProvider.objects.all():
            elastic_query = get_elastic_query(date, preprint_provider)
            resp = requests.post(f'{settings.SHARE_URL}api/v2/search/creativeworks/_search', json=elastic_query).json()

            report_es8 = PreprintSummaryReportEs8(
                cycle_coverage=f"{date:%Y.%m.%d}",
                provider_key=preprint_provider._id,
                preprint_count=resp['hits']['total'],
            )
            reports.append(report_es8)

            report = PreprintSummaryReport(
                report_date=date,
                provider_key=report_es8.provider_key,
                preprint_count=report_es8.preprint_count,
            )
            reports.append(report)
            logger.info('{} Preprints counted for the provider {}'.format(resp['hits']['total'], preprint_provider.name))

        return reports
