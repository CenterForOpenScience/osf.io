import pytz
import logging
from modularodm import Q
from dateutil.parser import parse
from datetime import datetime, timedelta

from website.app import init_app
from website.project.model import NodeLog
from framework.mongo.utils import paginated
from scripts.analytics.base import EventAnalytics

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class NodeLogEvents(EventAnalytics):

    @property
    def collection_name(self):
        return 'node_log_events'

    def get_events(self, date):
        """ Get all node logs from a given date for a 24 hour period,
        ending at the date given.
        """
        super(NodeLogEvents, self).get_events(date)

        # In the end, turn the date back into a datetime at midnight for queries
        date = datetime(date.year, date.month, date.day).replace(tzinfo=pytz.UTC)

        logger.info('Gathering node logs between {} and {}'.format(
            date, (date + timedelta(1)).isoformat()
        ))

        node_log_query = Q('date', 'lt', date + timedelta(1)) & Q('date', 'gte', date)

        node_logs = paginated(NodeLog, query=node_log_query)
        node_log_events = []
        for node_log in node_logs:
            log_date = node_log.date.replace(tzinfo=pytz.UTC)
            event = {
                'keen': {'timestamp': log_date.isoformat()},
                'date': log_date.isoformat(),
                'action': node_log.action
            }

            if node_log.user:
                event.update({'user_id': node_log.user._id})

            node_log_events.append(event)

        logger.info('NodeLogs counted. {} NodeLogs.'.format(len(node_log_events)))
        return node_log_events


def get_class():
    return NodeLogEvents


if __name__ == '__main__':
    init_app()
    node_log_events = NodeLogEvents()
    args = node_log_events.parse_args()
    date = parse(args.date).date() if args.date else None
    events = node_log_events.get_events(date)
    node_log_events.send_events(events)
