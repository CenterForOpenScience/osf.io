import time
import logging
import argparse
import importlib
from dateutil.parser import parse
from datetime import datetime, timedelta

from keen.client import KeenClient

from website.app import init_app
from website.settings import KEEN as keen_settings
from scripts.analytics.user_summary import get_events as user_events
from scripts.analytics.node_summary import get_events as node_events
from scripts.analytics.node_log_events import get_events as node_log_events

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_events_for_day(day, scripts=None):
    """Get an event summary for a certain 24 hour period.
     00:00UTC - 23:59:59UTC on the day provided.

     Default to explicitly imported and run analytic summary scripts,
     but optionally pass in the names of specific scripts to run.
     """
    logger.info('<---- Keen Summary Counts for {} ---->'.format(day.isoformat()))

    keen_events = {}
    if scripts:
        for script in scripts:
            try:
                script_events = importlib.import_module('scripts.analytics.{}'.format(script))
                keen_events.update({script: script_events.get_events(day)})
            except ImportError as e:
                logger.error(e)
                logger.error('Error importing script - make sure the script specified is inside of scripts/analytics')
    else:
        keen_events.update({'user_summary': user_events(day)})
        keen_events.update({'node_summary': node_events(day)})
        keen_events.update({'node_log_events': node_log_events(day)})

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
    parser.add_argument(
        '-as', '--analytics_scripts', nargs='+', dest='analytics_scripts', required=False,
        help='Enter the names of scripts inside scripts/analytics you would like to run separated by spaces (ex: -as user_summary node_summary)'
    )
    return parser.parse_args()

if __name__ == '__main__':
    now = datetime.utcnow()

    init_app()
    args = parse_args()
    end_date = parse(args.end_date) if args.end_date else now
    start_date = parse(args.start_date) if args.end_date else now - timedelta(1)
    scripts = args.analytics_scripts

    start_date = datetime(start_date.year, start_date.month, start_date.day)  # make sure the day starts at midnight

    main(start_date, end_date, scripts)
