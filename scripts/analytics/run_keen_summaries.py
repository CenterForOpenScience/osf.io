import time
import logging
import argparse
from dateutil.parser import parse
from datetime import datetime, timedelta

from keen.client import KeenClient

from website.app import init_app
from website.settings import KEEN as keen_settings
from scripts.analytics.user_summary import get_events as user_events
from scripts.analytics.node_summary import get_events as node_events
from scripts.analytics.node_log_count import get_events as node_log_events

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_events_for_day(day, scripts=None):
    """Get an event summary for a certain 24 hour period.
     00:00UTC - 23:59:59UTC on the day provided.

     Default to all known analytic summary scripts, but optionally
     pass in the names of specific scripts to run.
     """
    logger.info('<---- Keen Counts for {} ---->'.format(day.isoformat()))

    keen_events = {}

    if scripts:
        # try to imprt the scripts given the string name

        # raise a helpful error if the script named can't be found

        # assume that script has a "get_events" method and use that to add to keen_events

        # use the name of the script file as the assumed collection name
        pass
    else:
        keen_events.update({'user_summary': user_events(day)})
        keen_events.update({'node_summary': [node_events(day)]})
        keen_events.update({'node_log_events': [node_log_events(day)]})

    return keen_events


def yield_chunked_events(events):
    """ The keen API likes events in chunks no bigger than 5000 -
    Only yield that many at a time.
    """
    for i in range(0, len(events), 5000):
        yield events[i:i + 5000]


def main(start_date, end_date, scripts=None):
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
        events_for_day = get_events_for_day(day, scripts)
        for key, value in events_for_day.iteritems():
            for chunk in yield_chunked_events(value):
                client.add_events({key: chunk})
                time.sleep(1)
        day = day + timedelta(1)

def parse_args():
    parser = argparse.ArgumentParser(description='Populate keen counts!')
    parser.add_argument('-e', '--end', dest='end_date', required=False)
    parser.add_argument('-s', '--start', dest='start_date', required=False)
    parser.add_argument('-as', '--analytics_scripts', nargs='+', dest='analytics_scripts', required=False)
    return parser.parse_args()

if __name__ == '__main__':
    now = datetime.utcnow()

    init_app()
    args = parse_args()
    end_date = parse(args.end_date) if args.end_date else now
    start_date = parse(args.start_date) if args.end_date else now - datetime.timedelta(1)
    scripts = args.analytics_scripts

    main(start_date, end_date, scripts)
