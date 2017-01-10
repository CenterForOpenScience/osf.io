import pytz
import logging
from modularodm import Q
from dateutil.parser import parse
from datetime import datetime, timedelta

from website.app import init_app
from website.models import Node
from scripts.analytics.base import SummaryAnalytics


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class NodeSummary(SummaryAnalytics):

    @property
    def collection_name(self):
        return 'node_summary'

    def get_events(self, date):
        super(NodeSummary, self).get_events(date)

        # Convert to a datetime at midnight for queries and the timestamp
        timestamp_datetime = datetime(date.year, date.month, date.day).replace(tzinfo=pytz.UTC)
        query_datetime = timestamp_datetime + timedelta(1)

        node_query = (
            Q('is_deleted', 'ne', True) &
            Q('is_folder', 'ne', True) &
            Q('date_created', 'lt', query_datetime) &
            Q('is_collection', 'ne', True)
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
            'keen': {
                'timestamp': timestamp_datetime.isoformat()
            },
            'nodes': {
                'total': Node.find(node_query).count(),
                'public': Node.find(node_public_query).count(),
                'private': Node.find(node_private_query).count()
            },
            'projects': {
                'total': Node.find(project_query).count(),
                'public': Node.find(project_public_query).count(),
                'private': Node.find(project_private_query).count(),
            },
            'registered_nodes': {
                'total': Node.find(registration_query).count(),
                'public': Node.find(registered_node_public_query).count(),
                'embargoed': Node.find(registered_node_private_query).count(),
                'withdrawn': Node.find(registered_node_retracted_query).count(),
            },
            'registered_projects': {
                'total': Node.find(registered_project_query).count(),
                'public': Node.find(registered_project_public_query).count(),
                'embargoed': Node.find(registered_project_private_query).count(),
                'withdrawn': Node.find(registered_project_retracted_query).count(),
            }
        }

        logger.info(
            'Nodes counted. Nodes: {}, Projects: {}, Registered Nodes: {}, Registered Projects: {}'.format(
                totals['nodes']['total'],
                totals['projects']['total'],
                totals['registered_nodes']['total'],
                totals['registered_projects']['total']
            )
        )

        return [totals]


def get_class():
    return NodeSummary


if __name__ == '__main__':
    init_app()
    node_summary = NodeSummary()
    args = node_summary.parse_args()
    yesterday = args.yesterday
    if yesterday:
        date = (datetime.today() - timedelta(1)).date()
    else:
        date = parse(args.date).date() if args.date else None
    events = node_summary.get_events(date)
    node_summary.send_events(events)
