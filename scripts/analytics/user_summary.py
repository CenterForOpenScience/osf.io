import pytz
import logging
from dateutil.parser import parse
from datetime import datetime, timedelta

from modularodm import Q

from website.app import init_app
from website.models import User, NodeLog
from scripts.analytics.base import SummaryAnalytics

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

LOG_THRESHOLD = 11


# Modified from scripts/analytics/depth_users.py
def count_user_logs(user):
    logs = NodeLog.find(Q('user', 'eq', user._id))
    length = logs.count()
    if length > 0:
        item = logs[0]
        if item.action == 'project_created' and item.node.is_bookmark_collection:
            length -= 1
    return length


# Modified from scripts/analytics/depth_users.py
def get_number_of_depth_users(active_users):
    depth_users = 0
    for user in active_users:
        log_count = count_user_logs(user)
        if log_count >= LOG_THRESHOLD:
            depth_users += 1

    return depth_users


class UserSummary(SummaryAnalytics):

    @property
    def collection_name(self):
        return 'user_summary'

    def get_events(self, date):
        super(UserSummary, self).get_events(date)

        # Convert to a datetime at midnight for queries and the timestamp
        timestamp_datetime = datetime(date.year, date.month, date.day).replace(tzinfo=pytz.UTC)
        query_datetime = timestamp_datetime + timedelta(1)

        active_users = User.find(
                    Q('is_registered', 'eq', True) &
                    Q('password', 'ne', None) &
                    Q('merged_by', 'eq', None) &
                    Q('date_disabled', 'eq', None) &
                    Q('date_confirmed', 'ne', None) &
                    Q('date_confirmed', 'lt', query_datetime)
                )

        depth_users = get_number_of_depth_users(active_users)

        counts = {
            'keen': {
                'timestamp': timestamp_datetime.isoformat()
            },
            'status': {
                'active': active_users.count(),
                'depth': depth_users,
                'unconfirmed': User.find(
                    Q('date_registered', 'lt', query_datetime) &
                    Q('date_confirmed', 'eq', None)
                ).count(),
                'deactivated': User.find(
                    Q('date_disabled', 'ne', None) &
                    Q('date_disabled', 'lt', query_datetime)
                ).count()
            }
        }
        logger.info(
            'Users counted. Active: {}, Depth: {}, Unconfirmed: {}, Deactivated: {}'.format(
                counts['status']['active'],
                counts['status']['depth'],
                counts['status']['unconfirmed'],
                counts['status']['deactivated']
            )
        )
        return [counts]


def get_class():
    return UserSummary


if __name__ == '__main__':
    init_app()
    user_summary = UserSummary()
    args = user_summary.parse_args()
    date = parse(args.date).date() if args.date else None
    events = user_summary.get_events(date)
    user_summary.send_events(events)
