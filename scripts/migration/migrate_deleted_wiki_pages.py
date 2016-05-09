import logging
import sys

from modularodm import Q

from framework.transactions.context import TokuTransaction
from nose.tools import *
from tests.base import OsfTestCase
from tests.factories import ProjectFactory, AuthUserFactory, NodeWikiFactory
from website.app import init_app
from website.models import User, Node, NodeLog
from scripts import utils as script_utils

logger = logging.getLogger(__name__)

def get_targets():
    return NodeLog.find(Q('action', 'eq', NodeLog.WIKI_DELETED))

def migrate(targets, dry_run=True):
    # iterate over targets
    logs = targets
    nodes = set()
    for log in logs:
        nodes.add(log.node)
    for node in nodes:
        versions = node.wiki_pages_versions
        current = node.wiki_pages_current
        updated_versions = {}
        for wiki in node.wiki_pages_versions:
            if wiki in current:
                updated_versions[wiki] = versions[wiki]
        if not dry_run:
            node.wiki_pages_versions = updated_versions
            node.save()

    if dry_run:
        raise RuntimeError('Dry run, transaction rolled back.')


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


class TestMigrateDeletedWikiVersons(OsfTestCase):
    def setUp(self):
        super(TestMigrateDeletedWikiVersions, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user, is_public=True)
        # create a wiki page
        self.wiki = NodeWikiFactory(node=self.project_with_wikis)
        # make edits to wiki, then delete wiki so it is a target


    def test_get_targets(self):
        # Initial targets should include: user2, user3, user4, user5, user6 (5 in total)
        logs = get_targets()
        '''
        for log in logs:
            logging.info(user)
            logging.info(user.social['twitter'])
        logging.info(len(users))
        assert_equal(len(users), 5)
        '''

    def test_migrate(self):
        logs = get_targets()
        migrate(logs, dry_run=False)
        updated_logs = get_targets()
        # Make sure all nodes with deleted wikis have been migrated
        '''
        assert_equal(len(updated_logs), 0)
        # Make sure each user's twitter handle is as expected
        assert_equal(self.user1.social['twitter'], 'user1')
        # Reload all users
        self.user1.reload()
        self.user2.reload()
        self.user3.reload()
        self.user4.reload()
        self.user5.reload()
        self.user6.reload()
        assert_equal(self.user1.social['twitter'], 'user1')
        assert_equal(self.user2.social['twitter'], 'user2')
        assert_equal(self.user3.social['twitter'], 'user3')
        assert_equal(self.user4.social['twitter'], 'user4')
        assert_equal(self.user5.social['twitter'], 'user5')
        assert_equal(self.user6.social['twitter'], 'user6')
        assert_equal(self.user7.social['twitter'], '')
        '''