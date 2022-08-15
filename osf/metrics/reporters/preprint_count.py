import logging
import requests

from osf.metrics import PreprintSummaryReportV0
from ._base import DailyReporter

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

LOG_THRESHOLD = 11


class PreprintCountReporter(DailyReporter):
    def report(self, date):
        from osf.models import PreprintProvider

        elastic_query = {
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
                                'sources': None
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

        reports = []
        for preprint_provider in PreprintProvider.objects.all():
            name = preprint_provider.name if preprint_provider.name != 'Open Science Framework' else 'OSF'
            elastic_query['query']['bool']['must'][1]['match']['sources'] = name
            resp = requests.post('https://share.osf.io/api/v2/search/creativeworks/_search', json=elastic_query).json()
            reports.append(
                PreprintSummaryReportV0(
                    report_date=date,
                    provider_key=preprint_provider._id,
                    preprint_count=resp['hits']['total'],
                )
            )
            logger.info('{} Preprints counted for the provider {}'.format(resp['hits']['total'], preprint_provider.name))

        return reports

    def keen_events_from_report(self, report):
        event = {
            'provider': {
                'name': report.provider_key,
                'total': report.preprint_count,
            },
        }
        return {'preprint_summary': [event]}
