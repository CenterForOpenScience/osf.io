import pytz
import logging
from modularodm import Q
from dateutil.parser import parse
from datetime import datetime, timedelta

from website.models import User
from website.app import init_app
from framework.mongo.utils import paginated
from scripts.analytics.base import EventAnalytics

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class UserDomainEvents(EventAnalytics):

    @property
    def collection_name(self):
        return 'user_domain_events'

    def get_events(self, date):
        """ Get all node logs from a given date for a 24 hour period,
        ending at the date given.
        """
        super(UserDomainEvents, self).get_events(date)

        # In the end, turn the date back into a datetime at midnight for queries
        date = datetime(date.year, date.month, date.day).replace(tzinfo=pytz.UTC)

        logger.info('Gathering user domains between {} and {}'.format(
            date, (date + timedelta(1)).isoformat()
        ))
        user_query = (Q('date_confirmed', 'lt', date + timedelta(1)) &
                      Q('date_confirmed', 'gte', date) &
                      Q('username', 'ne', None))
        users = paginated(User, query=user_query)
        user_domain_events = []
        for user in users:
            user_date = user.date_confirmed.replace(tzinfo=pytz.UTC)
            event = {
                'keen': {'timestamp': user_date.isoformat()},
                'date': user_date.isoformat(),
                'domain': user.username.split('@')[-1]
            }
            user_domain_events.append(event)

        logger.info('User domains collected. {} users and their email domains.'.format(len(user_domain_events)))
        return user_domain_events


def get_class():
    return UserDomainEvents


if __name__ == '__main__':
    init_app()
    user_domain_events = UserDomainEvents()
    args = user_domain_events.parse_args()
    date = parse(args.date).date() if args.date else None
    events = user_domain_events.get_events(date)
    user_domain_events.send_events(events)
