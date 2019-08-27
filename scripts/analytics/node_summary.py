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
        from osf.models.spam import SpamStatus

        # Convert to a datetime at midnight for queries and the timestamp
        timestamp_datetime = datetime(date.year, date.month, date.day).replace(tzinfo=pytz.UTC)
        query_datetime = timestamp_datetime + timedelta(days=1)

        node_qs = Node.objects.filter(is_deleted=False, created__lte=query_datetime)
        registration_qs = Registration.objects.filter(is_deleted=False, created__lte=query_datetime)

        public_query = Q(is_public=True)
        private_query = Q(is_public=False)

        # node_query encompasses lte query_datetime
        daily_query = Q(created__gte=timestamp_datetime)
        retracted_query = Q(retraction__isnull=False)

        # `embargoed` used private status to determine embargoes, but old registrations could be private and unapproved registrations can also be private
        # `embargoed_v2` uses future embargo end dates on root
        embargo_v2_query = Q(root__embargo__end_date__gt=query_datetime)

        exclude_spam = ~Q(spam_status__in=[SpamStatus.SPAM, SpamStatus.FLAGGED])

        totals = {
            'keen': {
                'timestamp': timestamp_datetime.isoformat()
            },
            # Nodes - the number of projects and components
            'nodes': {
                'total': node_qs.count(),
                'total_excluding_spam': node_qs.filter(exclude_spam).count(),
                'public': node_qs.filter(public_query).count(),
                'private': node_qs.filter(private_query).count(),
                'total_daily': node_qs.filter(daily_query).count(),
                'total_daily_excluding_spam': node_qs.filter(daily_query).filter(exclude_spam).count(),
                'public_daily': node_qs.filter(public_query & daily_query).count(),
                'private_daily': node_qs.filter(private_query & daily_query).count(),
            },
            # Projects - the number of top-level only projects
            'projects': {
                'total': node_qs.get_roots().count(),
                'total_excluding_spam': node_qs.get_roots().filter(exclude_spam).count(),
                'public': node_qs.filter(public_query).get_roots().count(),
                'private': node_qs.filter(private_query).get_roots().count(),
                'total_daily': node_qs.filter(daily_query).get_roots().count(),
                'total_daily_excluding_spam': node_qs.filter(daily_query).get_roots().filter(exclude_spam).count(),
                'public_daily': node_qs.filter(public_query & daily_query).get_roots().count(),
                'private_daily': node_qs.filter(private_query & daily_query).get_roots().count(),
            },
            # Registered Nodes - the number of registered projects and components
            'registered_nodes': {
                'total': registration_qs.count(),
                'public': registration_qs.filter(public_query).count(),
                'embargoed': registration_qs.filter(private_query).count(),
                'embargoed_v2': registration_qs.filter(private_query & embargo_v2_query).count(),
                'withdrawn': registration_qs.filter(retracted_query).count(),
                'total_daily': registration_qs.filter(daily_query).count(),
                'public_daily': registration_qs.filter(public_query & daily_query).count(),
                'embargoed_daily': registration_qs.filter(private_query & daily_query).count(),
                'embargoed_v2_daily': registration_qs.filter(private_query & daily_query & embargo_v2_query).count(),
                'withdrawn_daily': registration_qs.filter(retracted_query & daily_query).count(),

            },
            # Registered Projects - the number of registered top level projects
            'registered_projects': {
                'total': registration_qs.get_roots().count(),
                'public': registration_qs.filter(public_query).get_roots().count(),
                'embargoed': registration_qs.filter(private_query).get_roots().count(),
                'embargoed_v2': registration_qs.filter(private_query & embargo_v2_query).get_roots().count(),
                'withdrawn': registration_qs.filter(retracted_query).get_roots().count(),
                'total_daily': registration_qs.filter(daily_query).get_roots().count(),
                'public_daily': registration_qs.filter(public_query & daily_query).get_roots().count(),
                'embargoed_daily': registration_qs.filter(private_query & daily_query).get_roots().count(),
                'embargoed_v2_daily': registration_qs.filter(private_query & daily_query & embargo_v2_query).get_roots().count(),
                'withdrawn_daily': registration_qs.filter(retracted_query & daily_query).get_roots().count(),
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
        date = (timezone.now() - timedelta(days=1)).date()
    else:
        date = parse(args.date).date() if args.date else None
    events = node_summary.get_events(date)
    node_summary.send_events(events)
