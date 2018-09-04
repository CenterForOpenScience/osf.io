import pytz

import logging
import requests
from dateutil.parser import parse
from datetime import datetime, timedelta

from django.db.models import Q
from website.app import init_app
from scripts.analytics.base import SummaryAnalytics
from osf.models import PageCounter


class DownloadCountSummary(SummaryAnalytics):

    @property
    def collection_name(self):
        return 'download_count_summary'

    def get_events(self, date):
        super(DownloadCountSummary, self).get_events(date)

        timestamp_datetime = datetime(date.year, date.month, date.day).replace(tzinfo=pytz.UTC)
        return [{
                'keen': {
                    'timestamp': timestamp_datetime.isoformat()
                },
                'files': {
                    'total': int(PageCounter.get_all_downloads_on_date(timestamp_datetime) or 0)
                },
        }]


def get_class():
    return DownloadCountSummary


if __name__ == '__main__':
    init_app()

    download_count_summary = DownloadCountSummary()
    args = download_count_summary.parse_args()
    yesterday = args.yesterday
    if yesterday:
        date = (timezone.now() - timedelta(1)).date()
    else:
        date = parse(args.date).date() if args.date else None
    events = download_count_summary.get_events(date)
    download_count_summary.send_events(events)
