import pytz
import logging
from dateutil.parser import parse
from datetime import datetime, timedelta
from django.db.models import Q

from osf.models import OSFUser
from website.app import init_app
from framework.database import paginated
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

    def get_events(self, date):
        super(UserSummary, self).get_events(date)

        # Convert to a datetime at midnight for queries and the timestamp
        timestamp_datetime = datetime(date.year, date.month, date.day).replace(tzinfo=pytz.UTC)
        query_datetime = timestamp_datetime + timedelta(1)

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

        counts = {
            'keen': {
                'timestamp': timestamp_datetime.isoformat()
            },
            'status': {
                'active': active_users,
                'depth': depth_users,
                'unconfirmed': OSFUser.objects.filter(date_registered__lt=query_datetime, date_confirmed__isnull=True).count(),
                'deactivated': OSFUser.objects.filter(date_disabled__isnull=False, date_disabled__lt=query_datetime).count(),
                'merged': OSFUser.objects.filter(date_registered__lt=query_datetime, merged_by__isnull=False).count(),
                'profile_edited': profile_edited
            }
        }
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
        date = (datetime.today() - timedelta(1)).date()
    else:
        date = parse(args.date).date() if args.date else None
    events = user_summary.get_events(date)
    user_summary.send_events(events)
