import pytz
import logging
from dateutil.parser import parse
from datetime import datetime, timedelta

from django.db.models import Q

from framework.encryption import ensure_bytes
from osf.models import Institution
from website.app import init_app
from scripts.analytics.base import SummaryAnalytics


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class InstitutionSummary(SummaryAnalytics):

    @property
    def collection_name(self):
        return 'institution_summary'

    def get_events(self, date):
        super(InstitutionSummary, self).get_events(date)

        institutions = Institution.objects.all()
        counts = []

        # Convert to a datetime at midnight for queries and the timestamp
        timestamp_datetime = datetime(date.year, date.month, date.day).replace(tzinfo=pytz.UTC)
        query_datetime = timestamp_datetime + timedelta(1)

        for institution in institutions:
            node_query = (
                Q(is_deleted=False) &
                Q(date_created__lt=query_datetime)
            )

            project_query = node_query
            public_query = Q(is_public=True)
            private_query = Q(is_public=False)
            node_public_query = node_query & public_query
            node_private_query = node_query & private_query
            project_public_query = project_query & public_query
            project_private_query = project_query & private_query
            count = {
                'institution': {
                    'id': ensure_bytes(institution._id),
                    'name': ensure_bytes(institution.name),
                },
                'users': {
                    'total': institution.osfuser_set.filter(is_active=True).count(),
                },
                'nodes': {
                    'total': institution.nodes.filter(node_query).exclude(type='osf.registration').count(),
                    'public': institution.nodes.filter(node_public_query).exclude(type='osf.registration').count(),
                    'private': institution.nodes.filter(node_private_query).exclude(type='osf.registration').count(),
                },
                'projects': {
                    'total': institution.nodes.filter(project_query).exclude(type='osf.registration').get_roots().count(),
                    'public': institution.nodes.filter(project_public_query).exclude(type='osf.registration').get_roots().count(),
                    'private': institution.nodes.filter(project_private_query).exclude(type='osf.registration').get_roots().count(),
                },
                'registered_nodes': {
                    'total': institution.nodes.filter(node_query).filter(type='osf.registration').count(),
                    'public': institution.nodes.filter(node_public_query).filter(type='osf.registration').count(),
                    'embargoed': institution.nodes.filter(node_private_query).filter(type='osf.registration').count(),
                },
                'registered_projects': {
                    'total': institution.nodes.filter(project_query).filter(type='osf.registration').get_roots().count(),
                    'public': institution.nodes.filter(project_public_query).filter(type='osf.registration').get_roots().count(),
                    'embargoed': institution.nodes.filter(project_private_query).filter(type='osf.registration').get_roots().count(),
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
