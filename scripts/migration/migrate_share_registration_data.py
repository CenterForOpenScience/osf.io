import logging
import sys

from framework.mongo import database as db
from framework.transactions.context import TokuTransaction
from scripts import utils as script_utils
from website.app import init_app
from website.models import Node
from website.project.tasks import on_registration_updated
from website import settings

logger = logging.getLogger(__name__)


def get_targets():
    return [p['_id'] for p in db['node'].find({'is_registration': True, 'is_deleted': False, 'is_public': True})]

def migrate(dry_run):
    assert settings.SHARE_URL, 'SHARE_URL must be set to migrate.'
    assert settings.SHARE_API_TOKEN, 'SHARE_API_TOKEN must be set to migrate.'
    targets = get_targets()
    target_count = len(targets)
    count = 0

    logger.info('Preparing to migrate {} registrations.'.format(target_count))
    for registration_id in targets:
        node = Node.load(registration_id)
        count += 1
        logger.info('{}/{} - {}'.format(count, target_count, node._id))
        if not dry_run:
            on_registration_updated(node)
        logger.info('Registration {} was sent to SHARE.'.format(node._id))

def main():
    dry_run = '--dry' in sys.argv
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    init_app(set_backends=True, routes=False)
    with TokuTransaction():
        migrate(dry_run)

if __name__ == "__main__":
    main()
