import logging
import sys

from modularodm import Q

from framework.transactions.context import TokuTransaction
from tests.base import OsfTestCase
from tests.factories import UserFactory
from website.app import init_app
from website.models import User
from scripts import utils as script_utils

logger = logging.getLogger(__name__)

def get_targets():
    return User.find(Q('social.twitter', 'contains', '@'))

def migrate(targets, dry_run=True):
    # iterate over targets
    # log things
    users = targets
    for user in users:
        twitter = user.social['twitter'].replace("@", "")
        logger.info('Setting `social.twitter` field of user {0} to {1}'.format(user._id, twitter))
        if not dry_run:
            user.social['twitter'] = twitter
            user.save()
    '''
    if dry_run:
        raise RuntimeError('Dry run, transaction rolled back.')
    '''

def main():
    dry_run = False
    if '--dry' in sys.argv:
        dry_run = True
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    init_app(set_backends=True, routes=False)
    with TokuTransaction():
        migrate(targets=get_targets(), dry_run=dry_run)

if __name__ == "__main__":
    main()

class TestMigrateTwitterHandles(OsfTestCase):
    def test_get_targets(self):
        #user = UserFactory()
        #user.social['twitter'] = "@@user"
        targets = get_targets()
        for user in targets:
            logging.info(user)

    def test_migrate(self):
        pass