import logging
import argparse
from dateutil.parser import parse
from datetime import datetime, timedelta

from keen.client import KeenClient

from website.app import init_app
from website.settings import KEEN as keen_settings
from scripts.analytics.user_count import count as user_count
from scripts.analytics.node_count import count as node_count
from scripts.analytics.node_log_count import get_node_log_events as node_log_count

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_events_for_day(day):
    """Get an event summary for a certain 24 hour period.
     00:00UTC - 23:59:59UTC on the day provided.
     """
    logger.info('<---- Keen Counts for {} ---->'.format(day.isoformat()))

    keen_events = {}
    keen_events.update({'user_count_analytics': user_count(day)})
    keen_events.update({'node_analytics': [node_count(day)]})
    keen_events.update({'node_log_analytics': [node_log_count(day)]})

    return keen_events


def yield_chunked_events(events):
    """ The keen API likes events in chunks no bigger than 5000 -
    Only yield that many at a time.
    """
    for i in range(0, len(events), 5000):
        yield events[i:i + 5000]


def main(start_date, end_date):
    keen_project = keen_settings['private']['project_id']
    write_key = keen_settings['private']['write_key']
    if keen_project and write_key:
        client = KeenClient(
            project_id=keen_project,
            write_key=write_key,
        )
    assert(client)

    day = start_date
    while day < end_date:
        events_for_day = get_events_for_day(day)
        for key, value in events_for_day.iteritems():
            for chunk in yield_chunked_events(value):
                client.add_events({key: chunk})
        day = day + timedelta(1)

def parse_args():
    parser = argparse.ArgumentParser(description='Populate keen counts!')
    parser.add_argument('-e', '--end', dest='end_date', required=False)
    parser.add_argument('-s', '--start', dest='start_date', required=False)
    return parser.parse_args()

if __name__ == '__main__':
    now = datetime.utcnow()

    init_app()
    args = parse_args()
    end_date = parse(args.end_date) if args.end_date else now
    start_date = parse(args.start_date) if args.end_date else now - datetime.timedelta(1)

    main(start_date, end_date)
