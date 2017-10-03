import django
django.setup()

import pytz
import logging
from dateutil.parser import parse
from datetime import datetime, timedelta

from django.db.models import Q
from django.utils import timezone

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
        query_datetime = timestamp_datetime + timedelta(days=1)

        daily_query = Q(date_created__gte=timestamp_datetime)
        node_query = Q(is_deleted=False) & Q(date_created__lt=query_datetime)
        project_query = node_query & Q(parent_nodes__isnull=True)
        public_query = Q(is_public=True)
        private_query = Q(is_public=False)
        reg_type_query = Q(type='osf.registration')

        node_public_query = node_query & public_query
        node_private_query = node_query & private_query
        project_public_query = project_query & public_query
        project_private_query = project_query & private_query

        # `embargoed` used private status to determine embargoes, but old registrations could be private and unapproved registrations can also be private
        # `embargoed_v2` uses future embargo end dates on root
        embargo_v2_query = Q(root__embargo__end_date__gt=query_datetime)

        for institution in institutions:
            count = {
                'institution': {
                    'id': ensure_bytes(institution._id),
                    'name': ensure_bytes(institution.name),
                },
                'users': {
                    'total': institution.osfuser_set.count(),
                    'total_daily': institution.osfuser_set.filter(date_confirmed__gte=timestamp_datetime, date_confirmed__lt=query_datetime).count(),
                },
                'nodes': {
                    'total': institution.nodes.filter(node_query).exclude(reg_type_query).count(),
                    'public': institution.nodes.filter(node_public_query).exclude(reg_type_query).count(),
                    'private': institution.nodes.filter(node_private_query).exclude(reg_type_query).count(),

                    'total_daily': institution.nodes.filter(node_query & daily_query).exclude(reg_type_query).count(),
                    'public_daily': institution.nodes.filter(node_public_query & daily_query).exclude(reg_type_query).count(),
                    'private_daily': institution.nodes.filter(node_private_query & daily_query).exclude(reg_type_query).count(),
                },
                'projects': {
                    'total': institution.nodes.filter(project_query).exclude(reg_type_query).count(),
                    'public': institution.nodes.filter(project_public_query).exclude(reg_type_query).count(),
                    'private': institution.nodes.filter(project_private_query).exclude(reg_type_query).count(),

                    'total_daily': institution.nodes.filter(project_query & daily_query).exclude(reg_type_query).count(),
                    'public_daily': institution.nodes.filter(project_public_query & daily_query).exclude(reg_type_query).count(),
                    'private_daily': institution.nodes.filter(project_private_query & daily_query).exclude(reg_type_query).count(),

                },
                'registered_nodes': {
                    'total': institution.nodes.filter(node_query & reg_type_query).count(),
                    'public': institution.nodes.filter(node_public_query & reg_type_query).count(),
                    'embargoed': institution.nodes.filter(node_private_query & reg_type_query).count(),
                    'embargoed_v2': institution.nodes.filter(node_private_query & reg_type_query & embargo_v2_query).count(),

                    'total_daily': institution.nodes.filter(node_query & reg_type_query & daily_query).count(),
                    'public_daily': institution.nodes.filter(node_public_query & reg_type_query & daily_query).count(),
                    'embargoed_daily': institution.nodes.filter(node_private_query & reg_type_query & daily_query).count(),
                    'embargoed_v2_daily': institution.nodes.filter(node_private_query & reg_type_query & daily_query & embargo_v2_query).count(),

                },
                'registered_projects': {
                    'total': institution.nodes.filter(project_query & reg_type_query).count(),
                    'public': institution.nodes.filter(project_public_query & reg_type_query).count(),
                    'embargoed': institution.nodes.filter(project_private_query & reg_type_query).count(),
                    'embargoed_v2': institution.nodes.filter(project_private_query & reg_type_query & embargo_v2_query).count(),

                    'total_daily': institution.nodes.filter(project_query & reg_type_query & daily_query).count(),
                    'public_daily': institution.nodes.filter(project_public_query & reg_type_query & daily_query).count(),
                    'embargoed_daily': institution.nodes.filter(project_private_query & reg_type_query & daily_query).count(),
                    'embargoed_v2_daily': institution.nodes.filter(project_private_query & reg_type_query & daily_query & embargo_v2_query).count(),
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
        date = (timezone.now() - timedelta(days=1)).date()
    else:
        date = parse(args.date).date() if args.date else None
    events = institution_summary.get_events(date)
    institution_summary.send_events(events)
