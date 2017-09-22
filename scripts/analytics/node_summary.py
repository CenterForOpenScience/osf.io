import django
django.setup()

from django.db.models import Q
import pytz
import logging
from dateutil.parser import parse
from datetime import datetime, timedelta
from django.utils import timezone

from website.app import init_app
from scripts.analytics.base import SummaryAnalytics


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class NodeSummary(SummaryAnalytics):

    @property
    def collection_name(self):
        return 'node_summary'

    def get_events(self, date):
        super(NodeSummary, self).get_events(date)
        from osf.models import Node, Registration

        # Convert to a datetime at midnight for queries and the timestamp
        timestamp_datetime = datetime(date.year, date.month, date.day).replace(tzinfo=pytz.UTC)
        query_datetime = timestamp_datetime + timedelta(1)

        node_query = Q(is_deleted=False, date_created__lte=query_datetime)
        project_query = node_query & Q(parent_nodes__isnull=True)

        public_query = Q(is_public=True)
        private_query = Q(is_public=False)

        # node_query encompasses lte query_datetime
        daily_query = Q(date_created__gte=timestamp_datetime)
        retracted_query = Q(retraction__isnull=False)

        node_public_query = node_query & public_query
        node_private_query = node_query & private_query
        node_daily_query = node_query & public_query

        node_retracted_query = node_query & retracted_query
        project_public_query = project_query & public_query
        project_private_query = project_query & private_query
        project_retracted_query = project_query & retracted_query

        # `embargoed` used private status to determine embargoes, but old registrations could be private and unapproved registrations can also be private
        # `embargoed_v2` uses future embargo end dates on root
        embargo_v2_query = Q(root__embargo__end_date__gt=query_datetime)

        totals = {
            'keen': {
                'timestamp': timestamp_datetime.isoformat()
            },
            # Nodes - the number of projects and components
            'nodes': {
                'total': Node.objects.filter(node_query).count(),
                'public': Node.objects.filter(node_public_query).count(),
                'private': Node.objects.filter(node_private_query).count(),
                'total_daily': Node.objects.filter(node_query & daily_query).count(),
                'public_daily': Node.objects.filter(node_public_query & daily_query).count(),
                'private_daily': Node.objects.filter(node_private_query & daily_query).count(),
            },
            # Projects - the number of top-level only projects
            'projects': {
                'total': Node.objects.filter(project_query).count(),
                'public': Node.objects.filter(project_public_query).count(),
                'private': Node.objects.filter(project_private_query).count(),
                'total_daily': Node.objects.filter(project_query & daily_query).count(),
                'public_daily': Node.objects.filter(project_public_query & daily_query).count(),
                'private_daily': Node.objects.filter(project_private_query & daily_query).count(),
            },
            # Registered Nodes - the number of registered projects and components
            'registered_nodes': {
                'total': Registration.objects.filter(node_query).count(),
                'public': Registration.objects.filter(node_public_query).count(),
                'embargoed': Registration.objects.filter(node_private_query).count(),
                'embargoed_v2': Registration.objects.filter(node_private_query & embargo_v2_query).count(),
                'withdrawn': Registration.objects.filter(node_retracted_query).count(),
                'total_daily': Registration.objects.filter(node_query & daily_query).count(),
                'public_daily': Registration.objects.filter(node_public_query & daily_query).count(),
                'embargoed_daily': Registration.objects.filter(node_private_query & daily_query).count(),
                'embargoed_v2_daily': Registration.objects.filter(node_private_query & daily_query & embargo_v2_query).count(),
                'withdrawn_daily': Registration.objects.filter(node_retracted_query & daily_query).count(),

            },
            # Registered Projects - the number of registered top level projects
            'registered_projects': {
                'total': Registration.objects.filter(project_query).count(),
                'public': Registration.objects.filter(project_public_query).count(),
                'embargoed': Registration.objects.filter(project_private_query).count(),
                'embargoed_v2': Registration.objects.filter(project_private_query & embargo_v2_query).count(),
                'withdrawn': Registration.objects.filter(project_retracted_query).count(),
                'total_daily': Registration.objects.filter(project_query & daily_query).count(),
                'public_daily': Registration.objects.filter(project_public_query & daily_query).count(),
                'embargoed_daily': Registration.objects.filter(project_private_query & daily_query).count(),
                'embargoed_v2_daily': Registration.objects.filter(project_private_query & daily_query & embargo_v2_query).count(),
                'withdrawn_daily': Registration.objects.filter(project_retracted_query & daily_query).count(),
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
        date = (timezone.now() - timedelta(1)).date()
    else:
        date = parse(args.date).date() if args.date else None
    events = node_summary.get_events(date)
    node_summary.send_events(events)
