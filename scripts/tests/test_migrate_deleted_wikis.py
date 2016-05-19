from nose.tools import *

from scripts.migration.migrate_deleted_wikis import get_targets, migrate


from tests.base import OsfTestCase
from tests.factories import ProjectFactory, UserFactory, Auth

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
