import argparse
from dateutil.parser import parse
from datetime import datetime, timedelta

from website.app import init_app
from website.settings import KEEN as keen_settings
from keen.client import KeenClient

from scripts.analytics.user_count import count as user_count
from scripts.analytics.addon_count import count as addon_count
from scripts.analytics.node_count import get_node_count as node_count
from scripts.analytics.node_count import parse_args

def get_events_for_day(day):
    keen_events = {}
    keen_events.update(user_count(day))
    keen_events.update(addon_count(day))
    keen_events.update({'node_analytics': node_count(day)})
    return keen_events

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
        client.add_events(get_events_for_day(day))
        day = day + timedelta(1)

def parse_args():
    parser = argparse.ArgumentParser(description='Populate keen counts!')
    parser.add_argument('-e', '--end', dest='end_date', required=False)
    parser.add_argument('-e', '--end', dest='start_date', required=True)
    return parser.parse_args()

if __name__ == '__main__':
    init_app()
    args = parse_args()
    end_date = parse(args.end_date) if args.end_date else datetime.now()
    start_date = parse(args.start_date)

    main(start_date, end_date)
