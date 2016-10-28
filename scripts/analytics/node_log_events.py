import time
import logging
import argparse
from modularodm import Q
from datetime import datetime, timedelta
from dateutil.parser import parse

from website.app import init_app
from website.project.model import NodeLog
from website.settings import KEEN as keen_settings
from keen.client import KeenClient

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_events(date):
    """ Get all node logs from a given date. Defaults to starting yesterday
    to today (both in UTC).
    """
    node_log_query = Q('date', 'lte', date) & Q('date', 'gt', date - timedelta(1))

    node_logs = NodeLog.find(node_log_query)
    node_log_events = []
    for node_log in node_logs:
        event = {
            'keen': {'timestamp': date.isoformat()},
            'date': node_log.date.isoformat(),
            'action': node_log.action
        }

        if node_log.user:
            event.update({'user_id': node_log.user._id})

        node_log_events.append(event)

    logger.info('NodeLogs counted. {} NodeLogs.'.format(len(node_log_events)))
    return node_log_events


def parse_args():
    parser = argparse.ArgumentParser(description='Get node log counts!')
    parser.add_argument('-d', '--date', dest='date', required=False)

    return parser.parse_args()


def yield_chunked_events(events):
    """ The keen API likes events in chunks no bigger than 5000 -
    Only yield that many at a time.
    """
    for i in range(0, len(events), 5000):
        yield events[i:i + 5000]


def main():
    """ Run when the script is accessed individually to send all results to keen.
    Gathers data and sends events in 5000 piece chunks.
    """
    today = datetime.datetime.utcnow().date()
    args = parse_args()
    date = parse(args.end_date).date() if args.date else today

    node_log_events = get_events(date)
    keen_project = keen_settings['private']['project_id']
    write_key = keen_settings['private']['write_key']
    if keen_project and write_key:
        client = KeenClient(
            project_id=keen_project,
            write_key=write_key,
        )

        for chunk in yield_chunked_events(node_log_events):
            client.add_events({'node_log_analytics': chunk})
            time.sleep(1)
    else:
        print(node_log_events)

if __name__ == '__main__':
    init_app()
    main()
