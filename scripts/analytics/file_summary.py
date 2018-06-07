import django
django.setup()

from django.db.models import Q
import logging
from dateutil.parser import parse
from datetime import datetime, timedelta
from django.utils import timezone

from website.app import init_app
from scripts.analytics.base import SummaryAnalytics


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class FileSummary(SummaryAnalytics):

    @property
    def collection_name(self):
        return 'file_summary'

    def get_events(self, date):
        super(FileSummary, self).get_events(date)
        from addons.osfstorage.models import OsfStorageFile

        # Convert to a datetime at midnight for queries and the timestamp
        timestamp_datetime = datetime(date.year, date.month, date.day).replace(tzinfo=timezone.utc)
        query_datetime = timestamp_datetime + timedelta(days=1)

        file_qs = OsfStorageFile.objects

        public_query = Q(node__is_public=True)
        private_query = Q(node__is_public=False)

        daily_query = Q(created__gte=timestamp_datetime)

        totals = {
            'keen': {
                'timestamp': timestamp_datetime.isoformat()
            },
            # OsfStorageFiles - the number of files on OsfStorage
            'osfstorage_files_including_quickfiles': {
                'total': file_qs.count(),
                'public': file_qs.filter(public_query).count(),
                'private': file_qs.filter(private_query).count(),
                'total_daily': file_qs.filter(daily_query).count(),
                'public_daily': file_qs.filter(public_query & daily_query).count(),
                'private_daily': file_qs.filter(private_query & daily_query).count(),
            },
        }

        logger.info(
            'OsfStorage Files counted. Files: {}'.format(
                totals['osfstorage_files_including_quickfiles']['total'],
            )
        )

        return [totals]


def get_class():
    return FileSummary


if __name__ == '__main__':
    init_app()
    file_summary = FileSummary()
    args = file_summary.parse_args()
    yesterday = args.yesterday
    if yesterday:
        date = (timezone.now() - timedelta(days=1)).date()
    else:
        date = parse(args.date).date() if args.date else None
    events = file_summary.get_events(date)
    file_summary.send_events(events)
