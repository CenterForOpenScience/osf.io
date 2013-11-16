from nose.tools import *  # PEP8 asserts

from tests.base import DbTestCase
from tests.factories import UserFactory, ProjectFactory, TagFactory

from framework.search.solr import solr
from website.search.solr_search import search_solr

class SolrTestCase(DbTestCase):

    def tearDown(self):
        solr.delete_all()
        solr.commit()

def query(term):
    results, _, _ = search_solr(term)
    return results.get('docs', [])

def query_user(name):
    term = 'user:"{}"'.format(name)
    return query(term)

class TestUserUpdate(SolrTestCase):

    def test_new_user(self):
        """Add a user, then verify that user is present in Solr.

        """
        # Create user
        user = UserFactory()

        # Verify that user has been added to Solr
        docs = query_user(user.fullname)
        assert_equal(len(docs), 1)

    def test_change_name(self):
        """Add a user, change her name, and verify that only the new name is
        found in Solr.

        """
        user = UserFactory()
        fullname_original = user.fullname
        user.fullname = user.fullname[::-1]
        user.save()

        docs_original = query_user(fullname_original)
        assert_equal(len(docs_original), 0)

        docs_current = query_user(user.fullname)
        assert_equal(len(docs_current), 1)

class TestProject(SolrTestCase):

    def setUp(self):
        self.user = UserFactory()
        self.project = ProjectFactory(title='Red Special', creator=self.user)

    def test_new_project_private(self):
        """Verify that a private project is not present in Solr.
        """
        docs = query(self.project.title)
        assert_equal(len(docs), 0)

    def test_make_public(self):
        """Make project public, and verify that it is present in Solr.
        """
        self.project.set_permissions('public')
        docs = query(self.project.title)
        assert_equal(len(docs), 1)

class TestPublicProject(SolrTestCase):

    def setUp(self):
        self.user = UserFactory()
        self.project = ProjectFactory(
            title='Red Special',
            creator=self.user,
            is_public=True
        )

    def test_make_private(self):
        """Make project public, then private, and verify that it is not present
        in Solr.
        """
        self.project.set_permissions('private')
        docs = query(self.project.title)
        assert_equal(len(docs), 0)

    def test_delete_project(self):
        """

        """
        self.project.remove_node(self.user)
        docs = query(self.project.title)
        assert_equal(len(docs), 0)

    def test_change_title(self):
        """

        """
        title_original = self.project.title
        self.project.set_title(self.project.title[::-1], self.user, save=True)

        docs = query(title_original)
        assert_equal(len(docs), 0)

        docs = query(self.project.title)
        assert_equal(len(docs), 1)

    def test_add_tag(self):

        tag_text = 'stonecoldcrazy'

        results, _, _ = search_solr('"{}"'.format(tag_text))
        assert_equal(len(results['docs']), 0)

        self.project.add_tag(tag_text, self.user, None)

        results, _, _ = search_solr('"{}"'.format(tag_text))
        assert_equal(len(results['docs']), 1)

    def test_remove_tag(self):

        tag_text = 'stonecoldcrazy'

        self.project.add_tag(tag_text, self.user, None)
        self.project.remove_tag(tag_text, self.user, None)

        results, _, _ = search_solr('"{}"'.format(tag_text))
        assert_equal(len(results['docs']), 0)

    def test_update_wiki(self):
        """

        """
        wiki_content = 'Hammer to fall'

        results, _, _ = search_solr('"{}"'.format(wiki_content))
        assert_equal(len(results['docs']), 0)

        self.project.update_node_wiki('home', wiki_content, self.user, None)

        results, _, _ = search_solr('"{}"'.format(wiki_content))
        assert_equal(len(results['docs']), 1)

    def test_add_contributor(self):
        """

        """
        user2 = UserFactory()

        results, _, _ = search_solr('"{}"'.format(user2.fullname))
        assert_equal(len(results['docs']), 0)

        self.project.add_contributor(user2, save=True)

        results, _, _ = search_solr('"{}"'.format(user2.fullname))
        assert_equal(len(results['docs']), 1)

    def test_remove_contributor(self):
        """

        """
        user2 = UserFactory()

        self.project.add_contributor(user2, save=True)
        self.project.remove_contributor(user2, self.user)

        results, _, _ = search_solr('"{}"'.format(user2.fullname))
        assert_equal(len(results['docs']), 0)
