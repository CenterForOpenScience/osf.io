import logging
import argparse
from modularodm import Q
from dateutil.parser import parse
from datetime import timedelta, datetime

from website.app import init_app
from website.models import Node
from website.settings import KEEN as keen_settings
from keen.client import KeenClient

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_events(date):
    """Count how many nodes exist.

    If the date is today, include all nodes up until the point when the script was called.
    Also include counts for public and private projects, and embargoed and withdrawn registrations
    with a date provided. These numbers are only accurate for the current time, since we can't know
    the public/private status on a given date in the past.

    If a date is given that isn't right now, include all nodes that were created up through the end of that date.
    Do not include counts for public and private projects, or embargoed and withdrawn registrations.
    """
    right_now = datetime.utcnow()
    is_today = True if right_now.day == date.day and right_now.month == date.month else False
    if not is_today:
        date = date + timedelta(1)

    logger.info('Gathering a count of nodes up until {}'.format(date.isoformat()))

    node_query = (
        Q('is_deleted', 'ne', True) &
        Q('is_folder', 'ne', True) &
        Q('date_created', 'lt', date)
    )

    registration_query = node_query & Q('is_registration', 'eq', True)
    non_registration_query = node_query & Q('is_registration', 'eq', False)
    project_query = non_registration_query & Q('parent_node', 'eq', None)
    registered_project_query = registration_query & Q('parent_node', 'eq', None)
    public_query = Q('is_public', 'eq', True)
    private_query = Q('is_public', 'eq', False)
    retracted_query = Q('retraction', 'ne', None)
    project_public_query = project_query & public_query
    project_private_query = project_query & private_query
    node_public_query = non_registration_query & public_query
    node_private_query = non_registration_query & private_query
    registered_node_public_query = registration_query & public_query
    registered_node_private_query = registration_query & private_query
    registered_node_retracted_query = registration_query & retracted_query
    registered_project_public_query = registered_project_query & public_query
    registered_project_private_query = registered_project_query & private_query
    registered_project_retracted_query = registered_project_query & retracted_query

    totals = {
        'nodes': {
            'total': Node.find(node_query).count(),
        },
        'projects': {
            'total': Node.find(project_query).count(),
        },
        'registered_nodes': {
            'total': Node.find(registration_query).count(),
        },
        'registered_projects': {
            'total': Node.find(registered_project_query).count(),
        }
    }

    if is_today:
        totals['nodes'].update({
            'public': Node.find(node_public_query).count(),
            'private': Node.find(node_private_query).count()
        })

        totals['projects'].update({
            'public': Node.find(project_public_query).count(),
            'private': Node.find(project_private_query).count(),
        })

        totals['registered_nodes'].update({
            'public': Node.find(registered_node_public_query).count(),
            'embargoed': Node.find(registered_node_private_query).count(),
            'withdrawn': Node.find(registered_node_retracted_query).count(),
        })

        totals['registered_projects'].update({
            'public': Node.find(registered_project_public_query).count(),
            'embargoed': Node.find(registered_project_private_query).count(),
            'withdrawn': Node.find(registered_project_retracted_query).count(),
        })

    if not is_today:
        totals['keen'] = {'timestamp': date.isoformat()}

    logger.info('Nodes counted. Nodes: {}, Projects: {}, Registered Nodes: {}, Registered Projects: {}'.format(totals['nodes']['total'], totals['projects']['total'], totals['registered_nodes']['total'], totals['registered_projects']['total']))
    return [totals]


def parse_args():
    parser = argparse.ArgumentParser(description='Get node counts!.')
    parser.add_argument('-d', '--date', dest='date', required=False)

    return parser.parse_args()


def main():
    args = parse_args()
    date = parse(args.date).date() if args.date else None
    if date:
        date = datetime(date.year, date.month, date.day)  # make sure the given day starts at midnight
    else:
        date = datetime.utcnow()
    node_count = get_events(date)
    keen_project = keen_settings['private']['project_id']
    write_key = keen_settings['private']['write_key']
    if keen_project and write_key:
        client = KeenClient(
            project_id=keen_project,
            write_key=write_key,
        )
        client.add_events({'node_analytics': node_count})
    else:
        print(node_count)


if __name__ == '__main__':
    init_app()
    main()
