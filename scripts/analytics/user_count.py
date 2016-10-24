import sys
import logging
from datetime import datetime
from dateutil.parser import parse

from modularodm import Q

from website.app import init_app
from website.models import User
from website.settings import KEEN as keen_settings
from keen.client import KeenClient

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def count(today):
    counts = {
        'keen': {
            'timestamp': today.isoformat()
        },
        'active_users': User.find(
            Q('is_registered', 'eq', True) &
            Q('password', 'ne', None) &
            Q('merged_by', 'eq', None) &
            Q('date_disabled', 'eq', None) &
            Q('date_confirmed', 'ne', None) &
            Q('date_confirmed', 'lt', today)
        ).count(),
        'unconfirmed_users': User.find(
            Q('date_registered', 'lt', today) &
            Q('date_confirmed', 'eq', None)
        ).count(),
        'deactivated_users': User.find(
            Q('date_disabled', 'ne', None) &
            Q('date_disabled', 'lt', today)
        ).count()
    }
    logger.info(
        'Users counted. Active: {}, Unconfirmed: {}, Deactivated: {}'.format(
            counts['active_users'],
            counts['unconfirmed_users'],
            counts['deactivated_users']
        )
    )
    return counts

def main(today):
    user_counts = count(today)
    keen_project = keen_settings['private']['project_id']
    write_key = keen_settings['private']['write_key']
    if keen_project and write_key:
        client = KeenClient(
            project_id=keen_project,
            write_key=write_key,
        )
        client.add_event('user_count_analytics', user_counts)
    else:
        print(user_counts)


if __name__ == '__main__':
    init_app()
    try:
        date = parse(sys.argv[1])
    except IndexError:
        date = datetime.utcnow()
    main(date)
