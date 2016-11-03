import logging
from dateutil.parser import parse
from datetime import datetime, timedelta

from modularodm import Q

from website.app import init_app
from website.models import User
from scripts.analytics.base import SummaryAnalytics

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class UserSummary(SummaryAnalytics):

    @property
    def collection_name(self):
        return 'user_summary'

    def get_events(self, date):
        super(UserSummary, self).get_events(date)

        # Convert to a datetime at midnight for queries and the timestamp
        timestamp_datetime = datetime(date.year, date.month, date.day)
        query_datetime = timestamp_datetime + timedelta(1)

        counts = {
            'keen': {
                'timestamp': timestamp_datetime.isoformat()
            },
            'active_users': User.find(
                Q('is_registered', 'eq', True) &
                Q('password', 'ne', None) &
                Q('merged_by', 'eq', None) &
                Q('date_disabled', 'eq', None) &
                Q('date_confirmed', 'ne', None) &
                Q('date_confirmed', 'lt', query_datetime)
            ).count(),
            'unconfirmed_users': User.find(
                Q('date_registered', 'lt', query_datetime) &
                Q('date_confirmed', 'eq', None)
            ).count(),
            'deactivated_users': User.find(
                Q('date_disabled', 'ne', None) &
                Q('date_disabled', 'lt', query_datetime)
            ).count()
        }
        logger.info(
            'Users counted. Active: {}, Unconfirmed: {}, Deactivated: {}'.format(
                counts['active_users'],
                counts['unconfirmed_users'],
                counts['deactivated_users']
            )
        )
        return [counts]


if __name__ == '__main__':
    init_app()
    user_summary = UserSummary()
    args = user_summary.parse_args()
    date = parse(args.date).date() if args.date else None
    events = user_summary.get_events(date)
    user_summary.send_events(events)
