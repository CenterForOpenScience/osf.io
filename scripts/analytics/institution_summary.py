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
        daily_query = Q(created__gte=timestamp_datetime)
        public_query = Q(is_public=True)
        private_query = Q(is_public=False)

        # `embargoed` used private status to determine embargoes, but old registrations could be private and unapproved registrations can also be private
        # `embargoed_v2` uses future embargo end dates on root
        embargo_v2_query = Q(root__embargo__end_date__gt=query_datetime)

        for institution in institutions:
            node_qs = institution.nodes.filter(is_deleted=False, created__lt=query_datetime).exclude(type='osf.registration')
            registration_qs = institution.nodes.filter(is_deleted=False, created__lt=query_datetime, type='osf.registration')

            count = {
                'institution': {
                    'id': ensure_bytes(institution._id),
                    'name': ensure_bytes(institution.name),
                },
                'users': {
                    'total': institution.osfuser_set.filter(is_active=True).count(),
                    'total_daily': institution.osfuser_set.filter(date_confirmed__gte=timestamp_datetime, date_confirmed__lt=query_datetime).count(),
                },
                'nodes': {
                    'total': node_qs.count(),
                    'public': node_qs.filter(public_query).count(),
                    'private': node_qs.filter(private_query).count(),

                    'total_daily': node_qs.filter(daily_query).count(),
                    'public_daily': node_qs.filter(public_query & daily_query).count(),
                    'private_daily': node_qs.filter(private_query & daily_query).count(),
                },
                # Projects use get_roots to remove children
                'projects': {
                    'total': node_qs.get_roots().count(),
                    'public': node_qs.filter(public_query).get_roots().count(),
                    'private': node_qs.filter(private_query).get_roots().count(),

                    'total_daily': node_qs.filter(daily_query).get_roots().count(),
                    'public_daily': node_qs.filter(public_query & daily_query).get_roots().count(),
                    'private_daily': node_qs.filter(private_query & daily_query).get_roots().count(),
                },
                'registered_nodes': {
                    'total': registration_qs.count(),
                    'public': registration_qs.filter(public_query).count(),
                    'embargoed': registration_qs.filter(private_query).count(),
                    'embargoed_v2': registration_qs.filter(private_query & embargo_v2_query).count(),

                    'total_daily': registration_qs.filter(daily_query).count(),
                    'public_daily': registration_qs.filter(public_query & daily_query).count(),
                    'embargoed_daily': registration_qs.filter(private_query & daily_query).count(),
                    'embargoed_v2_daily': registration_qs.filter(private_query & daily_query & embargo_v2_query).count(),
                },
                'registered_projects': {
                    'total': registration_qs.get_roots().count(),
                    'public': registration_qs.filter(public_query).get_roots().count(),
                    'embargoed': registration_qs.filter(private_query).get_roots().count(),
                    'embargoed_v2': registration_qs.filter(private_query & embargo_v2_query).get_roots().count(),

                    'total_daily': registration_qs.filter(daily_query).get_roots().count(),
                    'public_daily': registration_qs.filter(public_query & daily_query).get_roots().count(),
                    'embargoed_daily': registration_qs.filter(private_query & daily_query).get_roots().count(),
                    'embargoed_v2_daily': registration_qs.filter(private_query & daily_query & embargo_v2_query).get_roots().count(),
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
