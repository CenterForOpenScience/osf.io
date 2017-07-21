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
        super(PreprintSummary, self).get_events(date)
        from osf.models import PreprintService, PreprintProvider

        # Convert to a datetime at midnight for queries and the timestamp
        timestamp_datetime = datetime(date.year, date.month, date.day).replace(tzinfo=pytz.UTC)
        query_datetime = timestamp_datetime + timedelta(1)

        counts = []
        for preprint_provider in PreprintProvider.objects.all():
            preprint_for_provider_count = PreprintService.objects.filter(Q(
                node__isnull=False,
                node__is_deleted=False,
                provider___id=preprint_provider._id,
                date_created__lte=query_datetime)
            ).count()

            counts.append({
                'keen': {
                    'timestamp': timestamp_datetime.isoformat()
                },
                'provider': {
                    'name': preprint_provider.name,
                    'total': preprint_for_provider_count,
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
