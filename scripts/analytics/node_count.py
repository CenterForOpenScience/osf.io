import argparse
from modularodm import Q
from dateutil.parser import parse

from website.app import init_app
from website.models import Node
from website.settings import KEEN as keen_settings
from keen.client import KeenClient


def get_node_count(end_date=None):
    node_query = (
        Q('is_deleted', 'ne', True) &
        Q('is_folder', 'ne', True)
    )

    if end_date:
        node_query = node_query & Q('date_created', 'lt', end_date)

    registration_query = node_query & Q('is_registration', 'eq', True)
    non_registration_query = node_query & Q('is_registration', 'eq', False)
    project_query = non_registration_query & Q('parent_node', 'eq', None)
    registered_project_query = registration_query & Q('parent_node', 'eq', None)
    public_query = Q('is_public', 'eq', True)
    private_query = Q('is_public', 'eq', False)
    retracted_query = Q('retraction', 'ne', None)
    node_public_query = non_registration_query & public_query
    node_private_query = non_registration_query & private_query
    project_public_query = project_query & public_query
    project_private_query = project_query & private_query
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

    if not end_date:
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

    return totals


def parse_args():
    parser = argparse.ArgumentParser(description='Get node counts!.')
    parser.add_argument('-e', '--end', dest='end_date', required=False)

    return parser.parse_args()


def main():
    args = parse_args()

    end_date = parse(args['end_date']).date() if args.get('end_date') else None

    node_count = get_node_count(end_date)
    keen_project = keen_settings['private']['project_id']
    write_key = keen_settings['private']['write_key']
    if keen_project and write_key:
        client = KeenClient(
            project_id=keen_project,
            write_key=write_key,
        )
        client.add_event('node_analytics', node_count)
    else:
        print(node_count)


if __name__ == '__main__':
    init_app()
    main()
