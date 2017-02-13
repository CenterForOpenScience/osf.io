from itertools import chain
import pytz
import logging
from modularodm import Q
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
        from osf.models import AbstractNode, Node, Registration

        # Convert to a datetime at midnight for queries and the timestamp
        timestamp_datetime = datetime(date.year, date.month, date.day).replace(tzinfo=pytz.UTC)
        query_datetime = timestamp_datetime + timedelta(1)

        node_query = {'is_deleted': False, 'date_created__lte': query_datetime}
        project_query = dict(chain(node_query.iteritems(), {'parent_nodes__isnull': True}.iteritems()))

        public_query = {'is_public': True}
        private_query = {'is_public': False}
        retracted_query = {'retraction__isnull': False}

        node_public_query = dict(chain(node_query.iteritems(), public_query.iteritems()))
        node_private_query = dict(chain(node_query.iteritems(), private_query.iteritems()))
        node_retracted_query = dict(chain(node_query.iteritems(), retracted_query.iteritems()))
        project_public_query = dict(chain(project_query.iteritems(), public_query.iteritems()))
        project_private_query = dict(chain(project_query.iteritems(), private_query.iteritems()))
        project_retracted_query = dict(chain(project_query.iteritems(), retracted_query.iteritems()))

        totals = {
            'keen': {
                'timestamp': timestamp_datetime.isoformat()
            },
            'nodes': {
                'total': AbstractNode.objects.filter(**node_query).count(),
                'public': AbstractNode.objects.filter(**node_public_query).count(),
                'private': AbstractNode.objects.filter(**node_private_query).count()
            },
            'projects': {
                'total': Node.objects.filter(**project_query).count(),
                'public': Node.objects.filter(**project_public_query).count(),
                'private': Node.objects.filter(**project_private_query).count(),
            },
            'registered_nodes': {
                'total': Registration.objects.filter(**node_query).count(),
                'public': Registration.objects.filter(**node_public_query).count(),
                'embargoed': Registration.objects.filter(**node_private_query).count(),
                'withdrawn': Registration.objects.filter(**node_retracted_query).count(),
            },
            'registered_projects': {
                'total': Registration.objects.filter(**project_query).count(),
                'public': Registration.objects.filter(**project_public_query).count(),
                'embargoed': Registration.objects.filter(**project_private_query).count(),
                'withdrawn': Registration.objects.filter(**project_retracted_query).count(),
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
