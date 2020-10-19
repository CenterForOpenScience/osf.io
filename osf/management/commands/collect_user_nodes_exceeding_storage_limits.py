from django.core.management.base import BaseCommand
from django.contrib.contenttypes.models import ContentType
from django.db.models import Exists, OuterRef
import json
import logging
from tqdm import tqdm

from addons.osfstorage.models import OsfStorageFile
from api.caching.tasks import update_storage_usage_cache
from osf.models import Node
from osf.utils.permissions import ADMIN
from website.settings import StorageLimits

logger = logging.getLogger(__name__)


def get_admin_contributors(node):
    return node.get_group(ADMIN).user_set.filter(is_active=True).values_list('guids___id', flat=True)


def retrieve_user_nodes_exceeding_storage_limits():
    exceeded_user_node_dict = dict()

    files = OsfStorageFile.objects.filter(target_object_id=OuterRef('pk'), target_content_type_id=ContentType.objects.get(model='abstractnode').id)
    nodes = Node.objects.annotate(has_files=Exists(files)).filter(has_files=True)
    logger.info('Counting targets...')
    p_bar = tqdm(total=nodes.count())
    for node in nodes:
        update_storage_usage_cache(node.id, node._id)

        if (node.is_public and node.storage_limit_status >= StorageLimits.OVER_PUBLIC) or (not node.is_public and node.storage_limit_status >= StorageLimits.OVER_PRIVATE):
            contributors = get_admin_contributors(node)
            for user_id in contributors:
                user_public_nodes_exceeding = exceeded_user_node_dict.get(user_id, {}).get('public', list())
                user_private_nodes_exceeding = exceeded_user_node_dict.get(user_id, {}).get('private', list())

                if node.is_public:
                    user_public_nodes_exceeding.append(node._id)
                else:
                    user_private_nodes_exceeding.append(node._id)

                exceeded_user_node_dict.update({
                    user_id: {
                        'public': user_public_nodes_exceeding,
                        'private': user_private_nodes_exceeding
                    }
                })
        p_bar.update()
    p_bar.close()
    logger.info(f'Complete. Detected {len(exceeded_user_node_dict)} users to mail.')
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
