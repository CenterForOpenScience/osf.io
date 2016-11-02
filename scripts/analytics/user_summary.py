import argparse
import logging
from datetime import datetime, timedelta
from dateutil.parser import parse

from modularodm import Q

from website.app import init_app
from website.models import User
from website.settings import KEEN as keen_settings
from keen.client import KeenClient

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_events(date):
    """Count how many nodes exist.
    If no date is given, include all users up until the point when the script was called.
    If a date is given, include all users that were created up through the end of that date.
    """
    right_now = datetime.utcnow()
    is_today = True if right_now.day == date.day and right_now.month == date.month else False
    if not is_today:
        date = date + timedelta(1)

    logger.info('Gathering a count of users up until {}'.format(date.isoformat()))


    counts = {
        'keen': {
            'timestamp': date.isoformat()
        },
        'active_users': User.find(
            Q('is_registered', 'eq', True) &
            Q('password', 'ne', None) &
            Q('merged_by', 'eq', None) &
            Q('date_disabled', 'eq', None) &
            Q('date_confirmed', 'ne', None) &
            Q('date_confirmed', 'lt', date)
        ).count(),
        'unconfirmed_users': User.find(
            Q('date_registered', 'lt', date) &
            Q('date_confirmed', 'eq', None)
        ).count(),
        'deactivated_users': User.find(
            Q('date_disabled', 'ne', None) &
            Q('date_disabled', 'lt', date)
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

def parse_args():
    parser = argparse.ArgumentParser(description='Get user counts!.')
    parser.add_argument('-d', '--date', dest='date', required=False)

    return parser.parse_args()

def main(date):
    user_counts = get_events(date)
    keen_project = keen_settings['private']['project_id']
    write_key = keen_settings['private']['write_key']
    if keen_project and write_key:
        client = KeenClient(
            project_id=keen_project,
            write_key=write_key,
        )
        client.add_events({'user_count_analytics': user_counts})
    else:
        print(user_counts)


if __name__ == '__main__':
    init_app()
    args = parse_args()
    date = parse(args.date) if args.date else None
    if date:
        date = datetime(date.year, date.month, date.day)  # make sure the day starts at midnight
    else:
        date = datetime.utcnow()
    main(date)
