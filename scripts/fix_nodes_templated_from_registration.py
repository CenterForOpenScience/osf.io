import sys
import logging
from website.app import setup_django, init_app
from scripts import utils as script_utils
from django.db import transaction

setup_django()
from osf.models import AbstractNode


logger = logging.getLogger(__name__)


def do_migration():
    nodes = AbstractNode.objects.filter(template_node__type='osf.registration', type='osf.registration')
    # Avoid updating date_modified for migration
    date_modified_field = AbstractNode._meta.get_field('date_modified')
    date_modified_field.auto_now = False
    for node in nodes:
        logger.info(f'Casting Registration {node._id} to a Node')
        node._is_templated_clone = True
        node.recast('osf.node')
        node.save()
    date_modified_field.auto_now = True
    logger.info(f'Migrated {nodes.count()} nodes')


def main(dry=True):
    init_app(routes=False)
    with transaction.atomic():
        do_migration()
        if dry:
            raise Exception('Abort Transaction - Dry Run')


if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    # Finally run the migration
    main(dry=dry)
