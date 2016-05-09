import logging
import sys

from modularodm import Q

from framework.transactions.context import TokuTransaction
from nose.tools import *
from tests.base import OsfTestCase
from tests.factories import ProjectFactory, UserFactory, Auth
from website.app import init_app
from website.models import NodeLog
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


class TestMigrateDeletedWikis(OsfTestCase):
    def setUp(self):
        super(TestMigrateDeletedWikis, self).setUp()
        self.user = UserFactory()
        self.auth = Auth(user=self.user)
        self.project = ProjectFactory(creator=self.user)
        # Update home wiki (which can't be deleted) an a second wiki
        self.project.update_node_wiki('home', 'Hello world', self.auth)
        self.project.update_node_wiki('second', 'Hola mundo', self.auth)
        self.project.update_node_wiki('second', 'Hola mundo 2', self.auth)
        # Delete the second wiki to populate targets
        self.project.delete_node_wiki('second', self.auth)
        self.versions = self.project.wiki_pages_versions
        self.current = self.project.wiki_pages_current

    def test_get_targets(self):
        # Initial targets should include: user2, user3, user4, user5, user6 (5 in total)
        logs = get_targets()
        # assert len is equal to 1 log (deleting 'second' wiki on project)
        assert_equal(len(logs), 1)

    def test_migrate(self):
        # Assert 'home' has 2 versions
        # Assert 'second' has 2 versions
        assert_equal(len(self.versions['home']), 1)
        assert_equal(len(self.versions['second']), 2)
        logs = get_targets()
        migrate(logs, dry_run=False)
        self.project.reload()
        # Assert that 'home' has same versions as before
        self.versions = self.project.wiki_pages_versions
        assert_equal(len(self.versions['home']), 1)
        # need to assert that versions no longer contains 'second'
        assert_equal(len(self.versions), 1)
        # create another wiki with name 'second'
        self.project.update_node_wiki('second', 'Hola mundo 3', self.auth)
        # Make sure old versions not restored
        assert_equal(len(self.versions['second']), 1)
