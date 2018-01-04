from __future__ import division

import django
django.setup()
from keen import KeenClient
import logging
import pytz
import requests

from dateutil.parser import parse
from datetime import datetime, timedelta
from django.db.models import Q
from django.utils import timezone

from osf.models import OSFUser
from api.base import settings
from website.app import init_app
from framework.database import paginated
from framework import sentry
from scripts.analytics.base import SummaryAnalytics

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

LOG_THRESHOLD = 11


# Modified from scripts/analytics/depth_users.py
def count_user_logs(user):
    logs = user.logs.all()
    length = logs.count()
    if length == LOG_THRESHOLD:
        item = logs.first()
        if item.action == 'project_created' and item.node.is_bookmark_collection:
            length -= 1
    return length


class UserSummary(SummaryAnalytics):

    @property
    def collection_name(self):
        return 'user_summary'

    def calculate_stickiness(self, time_one, time_two):
        """Calculate the stickiness for date: (Unique users yesterday) / (Unique users over yesterday + 29 days) [total of 30 days]"""
        client = KeenClient(
            project_id=settings.KEEN['public']['project_id'],
            read_key=settings.KEEN['public']['read_key'],
        )

        time_two_iso = time_two.isoformat()
        last_thirty = client.count_unique(
            event_collection='pageviews',
            # beginning of yesterday - 29 days = 30 total days
            timeframe={'start': (time_one - timedelta(days=29)).isoformat(), 'end': time_two_iso},
            target_property='user.id',
            timezone='UTC'
        )

        last_one = client.count_unique(
            event_collection='pageviews',
            timeframe={'start': time_one.isoformat(), 'end': time_two_iso},
            target_property='user.id',
            timezone='UTC'
        )

        # avoid unlikely divide by 0 error
        if last_thirty == 0:
            return 0
        return last_one / last_thirty

    def get_events(self, date):
        super(UserSummary, self).get_events(date)

        # Convert to a datetime at midnight for queries and the timestamp
        timestamp_datetime = datetime(date.year, date.month, date.day).replace(tzinfo=pytz.UTC)
        query_datetime = timestamp_datetime + timedelta(days=1)

        active_user_query = (
            Q(is_registered=True) &
            Q(password__isnull=False) &
            Q(merged_by__isnull=True) &
            Q(date_disabled__isnull=True) &
            Q(date_confirmed__isnull=False) &
            Q(date_confirmed__lt=query_datetime)
        )

        active_users = 0
        depth_users = 0
        profile_edited = 0
        user_pages = paginated(OSFUser, query=active_user_query)
        for user in user_pages:
            active_users += 1
            log_count = count_user_logs(user)
            if log_count >= LOG_THRESHOLD:
                depth_users += 1
            if user.social or user.schools or user.jobs:
                profile_edited += 1
        new_users = OSFUser.objects.filter(is_active=True, date_confirmed__gte=timestamp_datetime, date_confirmed__lt=query_datetime)
        counts = {
            'keen': {
                'timestamp': timestamp_datetime.isoformat()
            },
            'status': {
                'active': active_users,
                'depth': depth_users,
                'new_users_daily': new_users.count(),
                'new_users_with_institution_daily': new_users.filter(affiliated_institutions__isnull=False).count(),
                'unconfirmed': OSFUser.objects.filter(date_registered__lt=query_datetime, date_confirmed__isnull=True).count(),
                'deactivated': OSFUser.objects.filter(date_disabled__isnull=False, date_disabled__lt=query_datetime).count(),
                'merged': OSFUser.objects.filter(date_registered__lt=query_datetime, merged_by__isnull=False).count(),
                'profile_edited': profile_edited,
            }
        }

        try:
            # Because this data reads from Keen it could fail if Keen read api fails while writing is still allowed
            counts['status']['stickiness'] = self.calculate_stickiness(timestamp_datetime, query_datetime)
        except requests.exceptions.ConnectionError:
            sentry.log_message('Unable to read from Keen. stickiness metric not collected for date {}'.format(timestamp_datetime.isoformat()))

        logger.info(
            'Users counted. Active: {}, Depth: {}, Unconfirmed: {}, Deactivated: {}, Merged: {}, Profile Edited: {}'.format(
                counts['status']['active'],
                counts['status']['depth'],
                counts['status']['unconfirmed'],
                counts['status']['deactivated'],
                counts['status']['merged'],
                counts['status']['profile_edited']
            )
        )
        return [counts]


def get_class():
    return UserSummary


if __name__ == '__main__':
    init_app()
    user_summary = UserSummary()
    args = user_summary.parse_args()
    yesterday = args.yesterday
    if yesterday:
        date = (timezone.now() - timedelta(days=1)).date()
    else:
        date = parse(args.date).date() if args.date else None
    events = user_summary.get_events(date)
    user_summary.send_events(events)
