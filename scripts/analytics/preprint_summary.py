import pytz

import logging
from dateutil.parser import parse
from datetime import datetime, timedelta

from django.db.models import Q
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
        #super(PreprintSummary, self).get_events(date)

        # Convert to a datetime at midnight for queries and the timestamp
        timestamp_datetime = datetime(date.year, date.month, date.day).replace(tzinfo=pytz.UTC)
        query_datetime = timestamp_datetime + timedelta(1)

        providers = {}
        for preprint_provider in PreprintProvider.objects.all():
            providers[preprint_provider.name] = PreprintService.objects.filter(Q(node__isnull=False,
                                                                                 node__is_deleted=False,
                                                                                 provider___id=preprint_provider._id)).count()

        return {
            'total': PreprintService.objects.all().count(),
            'providers': providers
        }


def get_class():
    return PreprintSummary


if __name__ == '__main__':

    init_app()

    from osf.models import PreprintService, PreprintProvider
    preprint_summary = PreprintSummary()
    args = preprint_summary.parse_args()
    args.date = '7-7-2017'
    yesterday = args.yesterday
    if yesterday:
        date = (datetime.today() - timedelta(1)).date()
    else:
        date = parse(args.date).date() if args.date else None
    events = preprint_summary.get_events(date)
    preprint_summary.send_events(events)
