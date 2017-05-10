import logging
import sys
import django
from django.db import transaction
django.setup()

from osf.models import Node
from scripts import utils as script_utils
from website import settings
from website.app import init_app

from keen import scoped_keys

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def valid_keen_key(keenio_read_key, node_id):
    try:
        ret = scoped_keys.decrypt(settings.KEEN['public']['master_key'], keenio_read_key)
        return ret['filters'][0]['property_value'] == node_id
    except Exception as error:
        logger.info('Error on {}:'.format(node_id))
        logger.exception(error)
        return True

def update():
    queryset = Node.objects.filter(preprints__isnull=False, is_public=True, is_deleted=False)
    print('Checking {} preprint nodes'.format(queryset.count()))
    count = 0
    updated_nodes = []
    for node in queryset:
        if not valid_keen_key(node.keenio_read_key, node._id):
            count += 1
            node.keenio_read_key = node.generate_keenio_read_key()
            node.save()
            updated_nodes.append(node._id)
    print('Updated {} node keen key(s), subset for QA = {}'.format(count, str(updated_nodes[0:10])))

def main():
    dry_run = '--dry' in sys.argv
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    init_app(set_backends=True, routes=False)
    with transaction.atomic():
        update()
        if dry_run:
            raise RuntimeError('Dry mode -- rolling back transaction')

if __name__ == '__main__':
    main()
