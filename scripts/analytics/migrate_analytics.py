# A script to migrate old keen analytics to a new collection, generate in-between points for choppy
# data, or a little of both

import os
import csv
import copy
import time
import logging
import argparse
import datetime
from dateutil.parser import parse
from keen.client import KeenClient

from website.settings import KEEN as keen_settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DELETE_WAIT_TIME = 10
VERY_LONG_TIMEFRAME = 'this_20_years'


def parse_args():
    parser = argparse.ArgumentParser(
        description='Enter a start date and end date to gather, smooth, and send back analytics for keen'
    )
    parser.add_argument('-s', '--start', dest='start_date')
    parser.add_argument('-e', '--end', dest='end_date')

    parser.add_argument('-t', '--transfer', dest='transfer_collection', action='store_true')
    parser.add_argument('-sc', '--source', dest='source_collection')
    parser.add_argument('-dc', '--destination', dest='destination_collection')
    parser.add_argument('-d', '--delete', dest='delete', action='store_true')

    parser.add_argument('-sm', '--smooth', dest='smooth_events', action='store_true')

    parser.add_argument('-sm', '--import', dest='import_events', action='store_true')

    parsed = parser.parse_args()

    validate_args(parsed)

    return parsed


def validate_args(args):
    """ Go through supplied command line args an determine if you have enough to continue

    :param args: argparse args object, to sift through and figure out if you need more info
    :return: None, just raise errors if it finds something wrong
    """
    if args.smooth and not (args.start_date and args.end_date):
        raise ValueError('To smooth data, please enter both a start date and end date.')

    if args.smooth and not args.source_colletion:
        raise ValueError('Please specify a source collection to smooth data from.')

    if args.transfer and not (args.source_colletion and args.destination_collection):
        raise ValueError('To transfer between keen collections, enter both a source and a destination collection.')

    if args.delete and not args.transfer:
        raise ValueError('To delete anything you will need to transfer analytics from one collection to another.')

    if any([args.start_date, args.end_date]) and not all([args.start_date, args.end_date]):
        raise ValueError('You must provide both a start and an end date if you provide either.')


def fill_in_event_gaps(collection_name, events):
    """ A method to help fill in gaps between events that might be far apart,
    so that one event happens per day.

    :param collection_name: keen collection events are from
    :param events: events to fill in gaps between
    :return: list of "generated and estimated" events to send that will fill in gaps.
    """

    given_days = [parse(event['keen']['timestamp']).date() for event in events]
    given_days.sort()
    events_to_add = []
    if given_days:
        if collection_name != 'addon_snapshot':
            first_event = [event for event in events if date_from_event_ts(event) == given_days[0]][0]
            events_to_add = generate_events_between_events(given_days, first_event)
        else:
            all_providers = list(set([event['provider']['name'] for event in events]))
            for provider in all_providers:
                first_event = [
                    event for event in events if date_from_event_ts(event) == given_days[0] and event['provider']['name'] == provider
                ][0]
                events_to_add += generate_events_between_events(given_days, first_event)
        logger.info('Generated {} events to add to the {} collection.'.format(len(events_to_add), collection_name))
    else:
        logger.info('Could not retrieve events for the date range you provided.')

    return events_to_add


def date_from_event_ts(event):
    return parse(event['keen']['timestamp']).date()


def generate_events_between_events(given_days, first_event):
    first_day = given_days[0]
    last_day = given_days[-1]
    next_day = first_day + datetime.timedelta(1)

    first_event['keen'].pop('created_at')
    first_event['keen'].pop('id')
    first_event['generated'] = True  # Add value to tag generated data

    generated_events = []
    while next_day < last_day:
        new_event = copy.deepcopy(first_event)
        new_event['keen']['timestamp'] = next_day.isoformat()
        if next_day not in given_days:
            generated_events.append(new_event)
        next_day += datetime.timedelta(1)

    return generated_events


def get_keen_client():
    keen_project = keen_settings['private'].get('project_id')
    read_key = keen_settings['private'].get('read_key')
    master_key = keen_settings['private'].get('master_key')
    write_key = keen_settings['private'].get('write_key')
    if keen_project and read_key and master_key:
        client = KeenClient(
            project_id=keen_project,
            read_key=read_key,
            master_key=master_key,
            write_key=write_key
        )
    else:
        raise ValueError('Cannot connect to Keen clients - all keys not provided.')

    return client


def extract_events_from_keen(client, event_collection, start_date=None, end_date=None):
    """ Get analytics from keen to use as a starting point for smoothing or transferring

    :param client: keen client to use for connection
    :param start_date: datetime object, datetime to start gathering from keen
    :param end_date: datetime object, datetime to stop gathering from keen
    :param event_collection: str, name of the event collection to gather from
    :return: a list of keen events to use in other methods
    """
    timeframe = VERY_LONG_TIMEFRAME
    if start_date and end_date:
        logger.info('Gathering events from the {} collection between {} and {}'.format(event_collection, start_date, end_date))
        timeframe = {"start": start_date.isoformat(), "end": end_date.isoformat()}
    else:
        logger.info('Gathering events from the {} collection using timeframe {}'.format(event_collection, VERY_LONG_TIMEFRAME))

    return client.extraction(event_collection, timeframe=timeframe)


def make_sure_keen_schemas_match(source_collection, destination_collection, keen_client):
    """ Helper function to check if two given collections have matching schemas in keen, to make sure
    they can be transfered between one another

    :param source_collection: str, collection that events are stored now
    :param destination_collection: str, collection to transfer to
    :param keen_client: KeenClient, instantiated for the connection
    :return: bool, if the two schemas match in keen
    """
    source_schema = keen_client.get_collection(source_collection)
    destination_schema = keen_client.get_collection(destination_collection)

    return source_schema == destination_schema


def transfer_events_to_another_collection(client, source_collection, destination_collection, delete=False):
    """ Transfer analytics from source collection to the destination collection.
    Will only work if the source and destination have the same schemas attached, will error if they don't

    :param client: KeenClient, client to use to make connection to keen
    :param source_collection: str, keen collection to transfer from
    :param destination_collection: str, keen collection to transfer to
    :param delete: bool, whether or not delete items from the old collection after transferred
    :return: None
    """
    schemas_match = make_sure_keen_schemas_match(source_collection, destination_collection, client)
    if not schemas_match:
        raise ValueError('The two provided schemas in keen do not match, you will need to do a bit more work.')

    events_from_source = extract_events_from_keen(client, source_collection)

    for event in events_from_source:
        event['keen'].pop('created_at')
        event['keen'].pop('id')

    add_events_to_keen(client, destination_collection, events_from_source)

    if delete:
        logger.warning('Will delete all events from the {} collection in {} seconds'.format(source_collection, DELETE_WAIT_TIME))
        for i in range(DELETE_WAIT_TIME):
            logger.info(i)
            time.sleep(1)
        client.delete_events(source_collection)

    logger.info(
        'Transferred {} events from the {} collection to the {} collection'.format(
            len(events_from_source),
            source_collection,
            destination_collection
        )
    )


def add_events_to_keen(client, collection, events):
    logger.info('Adding {} events to the {} collection...'.format(len(events), collection))
    client.add_events({collection: events})


def smooth_events_in_keen(client, source_collection, start_date, end_date):
    base_events = extract_events_from_keen(client, source_collection, start_date, end_date)
    events_to_fill_in = fill_in_event_gaps(source_collection, base_events)
    add_events_to_keen(client, source_collection, events_to_fill_in)


def main():
    """ Main function for moving around and adjusting analytics gotten from keen and sending them back to keen.

    Usage:
        * Transfer all events from the 'institution_analytics' to the 'institution_summary' collection:
            `python -m scripts.analytics.migrate_analytics.py -t -sc institution_analytics -dc institution_summary
        * Fill in the gaps in analytics for the 'addon_snapshot' collection between 2016-11-01 and 2016-11-15:
            `python -m scripts.analytics.migrate_analytics.py -sm -s 2016-11-01 -e 2016-11-15
    """
    args = parse_args()
    client = get_keen_client()

    if args.smooth:
        smooth_events_in_keen(client, args.source_colletion, parse(args.start_date), parse(args.end_date))
    if args.transfer:
        transfer_events_to_another_collection(client, args.source_collection, args.destination_collection, args.delete)


if __name__ == '__main__':
    # main()

    import_events_from_spreadsheet()
