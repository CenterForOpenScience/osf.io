# A script to migrate old keen analytics to a new collection, generate in-between points for choppy
# data, or a little of both

import os
import csv
import copy
import time
import pytz
import logging
import argparse
import datetime
from dateutil.parser import parse
from keen.client import KeenClient

from website.settings import KEEN as keen_settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

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

    parser.add_argument('-sm', '--smooth', dest='smooth_events', action='store_true')

    parser.add_argument('-o', '--old', dest='old_analytics', action='store_true')

    parser.add_argument('-d', '--dry', dest='dry', action='store_true')

    parser.add_argument('-r', '--reverse', dest='reverse', action='store_true')

    parser.add_argument('-re', '--removeevent', dest="remove_event")

    parsed = parser.parse_args()

    validate_args(parsed)

    return parsed


def validate_args(args):
    """ Go through supplied command line args an determine if you have enough to continue

    :param args: argparse args object, to sift through and figure out if you need more info
    :return: None, just raise errors if it finds something wrong
    """

    if args.dry:
        logger.info('Running analytics on DRY RUN mode! No data will actually be sent to Keen.')

    potential_operations = [args.smooth_events, args.transfer_collection, args.old_analytics]
    if len([arg for arg in potential_operations if arg]) > 1:
        raise ValueError('You may only choose one analytic type to run: transfer, smooth, or import old analytics.')

    if args.smooth_events and not (args.start_date and args.end_date):
        raise ValueError('To smooth data, please enter both a start date and end date.')

    if args.start_date and args.end_date:
        if parse(args.start_date) > parse(args.end_date):
            raise ValueError('Please enter an end date that is after the start date.')

    if args.smooth_events and not args.source_collection:
        raise ValueError('Please specify a source collection to smooth data from.')

    if args.transfer_collection and not (args.source_collection and args.destination_collection):
        raise ValueError('To transfer between keen collections, enter both a source and a destination collection.')

    if any([args.start_date, args.end_date]) and not all([args.start_date, args.end_date]):
        raise ValueError('You must provide both a start and an end date if you provide either.')

    if args.remove_event and not args.source_collection:
        raise ValueError('You must provide both a source collection to remove an event from.')


def fill_in_event_gaps(collection_name, events):
    """ A method to help fill in gaps between events that might be far apart,
    so that one event happens per day.

    :param collection_name: keen collection events are from
    :param events: events to fill in gaps between
    :return: list of "generated and estimated" events to send that will fill in gaps.
    """

    given_days = [parse(event['keen']['timestamp']).date() for event in events if not event.get('generated')]
    given_days.sort()
    date_chunks = [given_days[x-1:x+1] for x in range(1, len(given_days))]
    events_to_add = []
    if given_days:
        if collection_name == 'addon_snapshot':
            all_providers = list(set([event['provider']['name'] for event in events]))
            for provider in all_providers:
                for date_pair in date_chunks:
                    if date_pair[1] - date_pair[0] > datetime.timedelta(1) and date_pair[0] != date_pair[1]:
                        first_event = [
                            event for event in events if date_from_event_ts(event) == date_pair[0] and event['provider']['name'] == provider and not event.get('generated')
                            ]
                        if first_event:
                            events_to_add += generate_events_between_events(date_pair, first_event[0])
        elif collection_name == 'institution_summary':
            all_instutitions = list(set([event['institution']['name'] for event in events]))
            for institution in all_instutitions:
                for date_pair in date_chunks:
                    if date_pair[1] - date_pair[0] > datetime.timedelta(1) and date_pair[0] != date_pair[1]:
                        first_event = [
                            event for event in events if date_from_event_ts(event) == date_pair[0] and event['institution']['name'] == institution and not event.get('generated')
                            ]
                        if first_event:
                            events_to_add += generate_events_between_events(date_pair, first_event[0])
        else:
            for date_pair in date_chunks:
                if date_pair[1] - date_pair[0] > datetime.timedelta(1) and date_pair[0] != date_pair[1]:
                    first_event = [event for event in events if date_from_event_ts(event) == date_pair[0] and not event.get('generated')]
                    if first_event:
                        events_to_add += generate_events_between_events(date_pair, first_event[0])

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
        new_event['keen']['timestamp'] = datetime.datetime(next_day.year, next_day.month, next_day.day).replace(tzinfo=pytz.UTC).isoformat()
        if next_day not in given_days:
            generated_events.append(new_event)
        next_day += datetime.timedelta(1)

    if generated_events:
        logger.info('Generated {} events for the interval {} to {}'.format(
            len(generated_events),
            given_days[0].isoformat(),
            given_days[1].isoformat()
        )
    )
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


def transfer_events_to_another_collection(client, source_collection, destination_collection, dry, reverse=False):
    """ Transfer analytics from source collection to the destination collection.
    Will only work if the source and destination have the same schemas attached, will error if they don't

    :param client: KeenClient, client to use to make connection to keen
    :param source_collection: str, keen collection to transfer from
    :param destination_collection: str, keen collection to transfer to
    :param dry: bool, whether or not to make a dry run, aka actually send events to keen
    :return: None
    """
    schemas_match = make_sure_keen_schemas_match(source_collection, destination_collection, client)
    if not schemas_match:
        raise ValueError('The two provided schemas in keen do not match, you will need to do a bit more work.')

    events_from_source = extract_events_from_keen(client, source_collection)

    for event in events_from_source:
        event['keen'].pop('created_at')
        event['keen'].pop('id')

    if reverse:
        remove_events_from_keen(client, destination_collection, events_from_source, dry)
    else:
        add_events_to_keen(client, destination_collection, events_from_source, dry)

        logger.info(
            'Transferred {} events from the {} collection to the {} collection'.format(
                len(events_from_source),
                source_collection,
                destination_collection
            )
        )


def add_events_to_keen(client, collection, events, dry):
    logger.info('Adding {} events to the {} collection...'.format(len(events), collection))
    if not dry:
        client.add_events({collection: events})


def smooth_events_in_keen(client, source_collection, start_date, end_date, dry, reverse):
    base_events = extract_events_from_keen(client, source_collection, start_date, end_date)
    events_to_fill_in = fill_in_event_gaps(source_collection, base_events)
    if reverse:
        remove_events_from_keen(client, source_collection, events_to_fill_in, dry)
    else:
        add_events_to_keen(client, source_collection, events_to_fill_in, dry)


def remove_events_from_keen(client, source_collection, events, dry):
    for event in events:
        filters = [{'property_name': 'keen.timestamp', 'operator': 'eq', 'property_value': event['keen']['timestamp']}]

        # test to see if you get back the correct events from keen
        filtered_event = client.extraction(source_collection, filters=filters)
        if filtered_event:
            filtered_event = filtered_event[0]
            filtered_event['keen'].pop('id')
            filtered_event['keen'].pop('created_at')
            filtered_event['keen']['timestamp'] = filtered_event['keen']['timestamp'][:10]  # ends of timestamps differ
            event['keen']['timestamp'] = event['keen']['timestamp'][:10]
            if event != filtered_event:
                logger.error('Filtered event not equal to the event you have gathered, not removing...')
            else:
                logger.info('About to delete a generated event from the {} collection from the date {}'.format(
                    source_collection, event['keen']['timestamp']
                ))

                if not dry:
                    client.delete_events(source_collection, filters=filters)
        else:
            logger.info('No filtered event found.')


def import_old_events_from_spreadsheet():
    home = os.path.expanduser("~")
    spreadsheet_path = home + '/daily_user_counts.csv'

    key_map = {
        'active-users': 'active',
        'logs-gte-11-total': 'depth',
        'number_users': 'total_users',  # really is active - number_users
        'number_projects': 'projects.total',
        'number_projects_public': 'projects.public',
        'number_projects_registered': 'registrations.total',
        'Date': 'timestamp',
        'dropbox-users-enabled': 'enabled',
        'dropbox-users-authorized': 'authorized',
        'dropbox-users-linked': 'linked',
        'profile-edits': 'profile_edited'
    }

    with open(spreadsheet_path) as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        col_names = reader.next()

    dictReader = csv.DictReader(open(spreadsheet_path, 'rb'), fieldnames=col_names, delimiter=',')

    events = []
    for row in dictReader:
        event = {}
        for key in row:
            equiv_key = key_map.get(key, None)
            if equiv_key:
                event[equiv_key] = row[key]
        events.append(event)

    user_summary_cols = ['active', 'depth', 'total_users', 'timestamp', 'profile_edited']
    node_summary_cols = ['registrations.total', 'projects.total', 'projects.public', 'timestamp']
    addon_summary_cols = ['enabled', 'authorized', 'linked', 'timestamp']

    user_events = []
    node_events = []
    addon_events = []
    for event in events[3:]:  # The first few rows have blank and/or bad data because they're extra headers
        node_event = {}
        user_event = {}
        addon_event = {}
        for key, value in event.iteritems():
            if key in node_summary_cols:
                node_event[key] = value
            if key in user_summary_cols:
                user_event[key] = value
            if key in addon_summary_cols:
                addon_event[key] = value

        formatted_user_event = format_event(user_event, analytics_type='user')
        formatted_node_event = format_event(node_event, analytics_type='node')
        formatted_addon_event = format_event(addon_event, analytics_type='addon')

        if formatted_node_event:
            node_events.append(formatted_node_event)
        if formatted_user_event:
            user_events.append(formatted_user_event)
        if formatted_addon_event:
            addon_events.append(formatted_addon_event)

    logger.info(
        'Gathered {} old user events, {} old node events and {} old dropbox addon events for keen'.format(
            len(user_events),
            len(node_events),
            len(addon_events)
        )
    )

    return {'user_summary': user_events, 'node_summary': node_events, 'addon_snapshot': addon_events}


def comma_int(value):
    if value and value != 'MISSING':
        return int(value.replace(',', ''))


def format_event(event, analytics_type):
    user_event_template = {
        "status": {},
        "keen": {}
    }

    node_event_template = {
        "projects": {},
        "registered_projects": {},
        "keen": {}
    }

    addon_event_template = {
        "keen": {},
        "users": {}
    }

    template_to_use = None
    if analytics_type == 'user':
        template_to_use = user_event_template

        if event['active'] and event['active'] != 'MISSING':
            template_to_use['status']['active'] = comma_int(event['active'])
        if event['total_users'] and event['active']:
            template_to_use['status']['unconfirmed'] = comma_int(event['total_users']) - comma_int(event['active'])
        if event['profile_edited']:
            template_to_use['status']['profile_edited'] = comma_int(event['profile_edited'])
    elif analytics_type == 'node':
        template_to_use = node_event_template

        if event['projects.total']:
            template_to_use['projects']['total'] = comma_int(event['projects.total'])
        if event['projects.public']:
            template_to_use['projects']['public'] = comma_int(event['projects.public'])
        if event['registrations.total']:
            template_to_use['registered_projects']['total'] = comma_int(event['registrations.total'])
        if event['projects.total'] and event['projects.public']:
            template_to_use['projects']['private'] = template_to_use['projects']['total'] - template_to_use['projects']['public']
    elif analytics_type == 'addon':
        template_to_use = addon_event_template

        if event['enabled']:
            template_to_use['users']['enabled'] = comma_int(event['enabled'])
        if event['authorized']:
            template_to_use['users']['authorized'] = comma_int(event['authorized'])
        if event['linked']:
            template_to_use['users']['linked'] = comma_int(event['linked'])

        if event['authorized'] or event['enabled'] or event['linked']:
            template_to_use["provider"] = {"name": "dropbox"}

    template_to_use['keen']['timestamp'] = parse(event['timestamp']).replace(hour=12, tzinfo=pytz.UTC).isoformat()
    template_to_use['imported'] = True

    formatted_event = {key: value for key, value in template_to_use.items() if value}
    if len(formatted_event.items()) > 2:  # if there's more than just the auto-added timestamp for keen
        return template_to_use


def remove_event_from_keen(client, source_collection, event_id):
    filters = [{'property_name': 'keen.id', 'operator': 'eq', 'property_value': event_id}]
    client.delete_events(source_collection, filters=filters)


def parse_and_send_old_events_to_keen(client, dry, reverse):
    old_events = import_old_events_from_spreadsheet()

    for key, value in old_events.iteritems():
        if reverse:
            remove_events_from_keen(client, key, value, dry)
        else:
            add_events_to_keen(client, key, value, dry)


def main():
    """ Main function for moving around and adjusting analytics gotten from keen and sending them back to keen.

    Usage:
        * Transfer all events from the 'institution_analytics' to the 'institution_summary' collection:
            `python -m scripts.analytics.migrate_analytics -d -t -sc institution_analytics -dc institution_summary`
        * Fill in the gaps in analytics for the 'addon_snapshot' collection between 2016-11-01 and 2016-11-15:
            `python -m scripts.analytics.migrate_analytics -d -sm -sc addon_snapshot -s 2016-11-01 -e 2016-11-15`
        * Reverse the above action by adding -r:
            `python -m scripts.analytics.migrate_analytics -d -sm -sc addon_snapshot -s 2016-11-01 -e 2016-11-15 -r`
        * Parse old analytics from the old analytics CSV stored on your filesystem:
            `python -m scripts.analytics.migrate_analytics -o -d`
    """
    args = parse_args()
    client = get_keen_client()

    dry = args.dry
    reverse = args.reverse

    if args.remove_event:
        remove_event_from_keen(client, args.source_collection, args.remove_event)
    if args.smooth_events:
        smooth_events_in_keen(client, args.source_collection, parse(args.start_date), parse(args.end_date), dry, reverse)
    elif args.transfer_collection:
        transfer_events_to_another_collection(client, args.source_collection, args.destination_collection, dry, reverse)
    elif args.old_analytics:
        parse_and_send_old_events_to_keen(client, dry, reverse)


if __name__ == '__main__':
    main()
