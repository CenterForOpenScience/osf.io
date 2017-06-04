from nose.tools import *

from scripts.migration.migrate_deleted_wikis import get_targets, migrate

from tests.base import OsfTestCase
from tests.factories import ProjectFactory, UserFactory, Auth


class TestMigrateDeletedWikis(OsfTestCase):

    # Whenever wiki is deleted, increment this variable to account for
    # fact that NodeLog.WIKI_DELETED is added to each time
    times_wiki_deleted = 0

    def setUp(self):
        super(TestMigrateDeletedWikis, self).setUp()
        self.user = UserFactory()
        self.auth = Auth(user=self.user)
        self.project = ProjectFactory(creator=self.user)
        # Update home wiki (which can't be deleted) an a second wiki
        self.project.update_node_wiki('home', 'Hello world', self.auth)
        self.project.update_node_wiki('second', 'Hola mundo', self.auth)
        self.project.update_node_wiki('second', 'Hola mundo 2', self.auth)
        self.versions = self.project.wiki_pages_versions
        self.current = self.project.wiki_pages_current

    def test_get_targets(self):
        # delete second wiki to add something to targets
        self.project.delete_node_wiki('second', self.auth)
        TestMigrateDeletedWikis.times_wiki_deleted += 1
        # Initial targets should include: user2, user3, user4, user5, user6 (5 in total)
        logs = get_targets()
        # assert len is equal to number of time a wiki is deleted in entire test script
        assert_equal(len(logs), TestMigrateDeletedWikis.times_wiki_deleted)

    def test_delete_wiki_node(self):
        self.project.delete_node_wiki('second', self.auth)
        TestMigrateDeletedWikis.times_wiki_deleted += 1
        self.versions = self.project.wiki_pages_versions
        assert_true('second' not in self.versions)

    def test_migrate(self):
        logs = get_targets()
        migrate(logs, dry_run=False)
        self.project.reload()
        # Ensure that wiki pages that were targeted are not in versions
        for log in logs:
            node = log.node
            assert_true(node.title not in self.project.wiki_pages_versions)

    def test_migration_does_not_affect_home(self):
        logs = get_targets()
        migrate(logs, dry_run=False)
        self.project.reload()
        # Assert that 'home' has same versions as before
        self.versions = self.project.wiki_pages_versions
        assert_equal(len(self.versions['home']), 1)

    def test_deleted_wiki_versions_not_restored(self):
        self.project.delete_node_wiki('second', self.auth)
        TestMigrateDeletedWikis.times_wiki_deleted += 1
        # create another wiki with name 'second'
        self.project.update_node_wiki('second', 'Hola mundo 3', self.auth)
        # Make sure old versions not restored
        assert_equal(len(self.versions['second']), 1)