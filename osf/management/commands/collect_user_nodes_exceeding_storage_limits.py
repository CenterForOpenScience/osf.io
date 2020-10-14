from django.core.management.base import BaseCommand
import json
import logging

from api.caching.tasks import update_storage_usage_cache
from osf.models import Node
from website.settings import StorageLimits

logger = logging.getLogger(__name__)


def get_write_admin_contributors(node):
    write_admin_contributor_set = set()
    for contributor in node.contributor_set.all():
        if contributor.permission in ['write', 'admin']:
            write_admin_contributor_set.add(contributor.user._id)
    return write_admin_contributor_set


def retrieve_user_nodes_exceeding_storage_limits():
    exceeded_user_node_dict = dict()

    for node in Node.objects.filter(type='osf.node'):
        # if node.storage_limit_status is StorageLimits.NOT_CALCULATED:
        storage_usage = node.storage_usage
        if storage_usage is None:
            logger.info(f'{node._id}\'s storage is uncalculated. Calculating storage now.')
            update_storage_usage_cache(node.id, node._id)

        if node.is_public:
            if node.storage_limit_status >= StorageLimits.OVER_PUBLIC:
                contributors = get_write_admin_contributors(node)
                for user_id in contributors:
                    if user_id in exceeded_user_node_dict:
                        user_public_nodes_exceeding = exceeded_user_node_dict[user_id]['public'].append(node._id)
                        user_private_nodes_exceeding = exceeded_user_node_dict[user_id]['private']
                    else:
                        user_public_nodes_exceeding = [node._id]
                        user_private_nodes_exceeding = []
                    exceeded_user_node_dict.update({
                        user_id: {
                            'public': user_public_nodes_exceeding,
                            'private': user_private_nodes_exceeding
                        }
                    })
        else:
            if node.storage_limit_status >= StorageLimits.OVER_PRIVATE:
                contributors = get_write_admin_contributors(node)
                for user_id in contributors:
                    if user_id in exceeded_user_node_dict:
                        user_public_nodes_exceeding = exceeded_user_node_dict[user_id]['public']
                        user_private_nodes_exceeding = exceeded_user_node_dict[user_id]['private'].append(node._id)
                    else:
                        user_public_nodes_exceeding = []
                        user_private_nodes_exceeding = [node._id]

                    exceeded_user_node_dict.update({
                        user_id: {
                            'public': user_public_nodes_exceeding,
                            'private': user_private_nodes_exceeding
                        }
                    })
    return exceeded_user_node_dict


class Command(BaseCommand):
    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--path',
            dest='path',
            help='Path for the json output',
        )

    def handle(self, *args, **options):
        path = options.get('path', None)
        data = retrieve_user_nodes_exceeding_storage_limits()
        if path:
            with open(path, 'w') as f:
                json.dump(data, f)
        else:
            print(json.dumps(data))
