import pytz
import logging
from modularodm import Q
from dateutil.parser import parse
from datetime import datetime, timedelta

from website.app import init_app
from website.models import User, Node, Institution
from scripts.analytics.base import SummaryAnalytics


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class InstitutionSummary(SummaryAnalytics):

    @property
    def collection_name(self):
        return 'institution_summary'

    def get_institutions(self):
        institutions = Institution.find(Q('_id', 'ne', None))
        return institutions

    def get_events(self, date):
        super(InstitutionSummary, self).get_events(date)
        from osf.models import AbstractNode, Registration

        institutions = self.get_institutions()
        counts = []

        # Convert to a datetime at midnight for queries and the timestamp
        timestamp_datetime = datetime(date.year, date.month, date.day).replace(tzinfo=pytz.UTC)
        query_datetime = timestamp_datetime + timedelta(1)

        for institution in institutions:
            user_query = Q('affiliated_institutions', 'eq', institution)
            node_query = (
                Q('is_deleted', 'ne', True) &
                Q('date_created', 'lt', query_datetime)
            )

            project_query = node_query & Q('parent_nodes', 'eq', None)
            public_query = Q('is_public', 'eq', True)
            private_query = Q('is_public', 'eq', False)
            node_public_query = node_query & public_query
            node_private_query = node_query & private_query
            project_public_query = project_query & public_query
            project_private_query = project_query & private_query
            count = {
                'institution':{
                    'id': institution._id,
                    'name': institution.name,
                },
                'users': {
                    'total': User.find(user_query).count(),
                },
                'nodes': {
                    'total':AbstractNode.find_by_institutions(institution, node_query).count(),
                    'public': AbstractNode.find_by_institutions(institution, node_public_query).count(),
                    'private': AbstractNode.find_by_institutions(institution, node_private_query).count(),
                },
                'projects': {
                    'total': Node.find_by_institutions(institution, project_query).count(),
                    'public': Node.find_by_institutions(institution, project_public_query).count(),
                    'private': Node.find_by_institutions(institution, project_private_query).count(),
                },
                'registered_nodes': {
                    'total': Registration.find_by_institutions(institution, node_query).count(),
                    'public': Registration.find_by_institutions(institution, node_public_query).count(),
                    'embargoed': Registration.find_by_institutions(institution, node_private_query).count(),
                },
                'registered_projects': {
                    'total': Registration.find_by_institutions(institution, project_query).count(),
                    'public': Registration.find_by_institutions(institution, project_public_query).count(),
                    'embargoed': Registration.find_by_institutions(institution, project_private_query).count(),
                },
                'keen': {
                    'timestamp': timestamp_datetime.isoformat()
                }
            }

            logger.info(
                '{} Nodes counted. Nodes: {}, Projects: {}, Registered Nodes: {}, Registered Projects: {}'.format(
                    count['institution']['name'],
                    count['nodes']['total'],
                    count['projects']['total'],
                    count['registered_nodes']['total'],
                    count['registered_projects']['total']
                )
            )

            counts.append(count)
        return counts


def get_class():
    return InstitutionSummary


if __name__ == '__main__':
    init_app()
    institution_summary = InstitutionSummary()
    args = institution_summary.parse_args()
    yesterday = args.yesterday
    if yesterday:
        date = (datetime.today() - timedelta(1)).date()
    else:
        date = parse(args.date).date() if args.date else None
    events = institution_summary.get_events(date)
    institution_summary.send_events(events)
