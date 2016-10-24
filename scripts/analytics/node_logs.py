import time
import logging
import argparse
from modularodm import Q
from datetime import datetime
from dateutil.parser import parse

from website.app import init_app
from website.project.model import NodeLog
from website.settings import KEEN as keen_settings
from keen.client import KeenClient

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def get_node_log_events(end_date):

    node_logs = NodeLog.find(Q('date', 'lt', end_date))

    node_log_events = []
    for node_log in node_logs:
        event = {
            'keen': {'timestamp': end_date.isoformat()},
            'date': node_log.date.isoformat(),
            'action': node_log.action
        }

        if node_log.user:
            event.update({'user_id': node_log.user._id})

        node_log_events.append(event)

    return node_log_events


def parse_args():
    parser = argparse.ArgumentParser(description='Get node log counts!')
    parser.add_argument('-e', '--end', dest='end_date', required=False)

    return parser.parse_args()


def main():
    args = parse_args()
    end_date = parse(args.end_date) if args.end_date else datetime.today()

    node_log_events = get_node_log_events(end_date)
    keen_project = keen_settings['private']['project_id']
    write_key = keen_settings['private']['write_key']
    if keen_project and write_key:
        client = KeenClient(
            project_id=keen_project,
            write_key=write_key,
        )

        start, stop, total_sent = 0, 5000, 0
        while total_sent <= len(node_log_events):
            keen_payload = {'node_log_analytics': node_log_events[start:stop]}
            client.add_events(keen_payload)
            start += 5000
            stop += 5000
            total_sent += 5000
            time.sleep(10)
    else:
        print(node_log_events)

    logger.info('NodeLogs counted. {} NodeLogs.'.format(len(node_log_events)))

if __name__ == '__main__':
    init_app()
    main()
