import unittest
from nose.tools import *  # PEP8 asserts

from tests.base import OsfTestCase
from tests.factories import UserFactory, ProjectFactory, UnregUserFactory

from website.search.utils import clean_solr_doc
from framework.auth.decorators import Auth
from website import settings

#if settings.SEARCH_ENGINE is not None: #Uncomment to force elasticsearch to load for testing
#    settings.SEARCH_ENGINE = 'elastic'
import website.search.search as search
#reload(search)

@unittest.skipIf(settings.SEARCH_ENGINE != 'elastic', 'Elastic search disabled')
class SearchTestCase(OsfTestCase):

        
    def tearDown(self):
        search.delete_all() 


def query(term):
    results, _, _ = search.search(term)
    return results


def query_user(name):
    term = 'user:"{}"'.format(name)
    return query(term)

@unittest.skipIf(settings.SEARCH_ENGINE != 'elastic', 'Elastic search disabled')
class TestUserUpdate(SearchTestCase):

    def test_new_user(self):
        """Add a user, then verify that user is present in search

        """
        # Create user
        user = UserFactory(fullname='David Bowie')
        # Verify that user has been added to Solr
        docs = query_user(user.fullname)
        assert_equal(len(docs), 1)

    def test_change_name(self):
        """Add a user, change her name, and verify that only the new name is
        found in search.

        """
        user = UserFactory(fullname='Barry Mitchell')
        fullname_original = user.fullname
        user.fullname = user.fullname[::-1]
        user.save()

        docs_original = query_user(fullname_original)
        assert_equal(len(docs_original), 0)

        docs_current = query_user(user.fullname)
        assert_equal(len(docs_current), 1)

@unittest.skipIf(settings.SEARCH_ENGINE != 'elastic', 'Elastic search disabled')
class TestProject(SearchTestCase):

    def setUp(self):
        self.user = UserFactory(fullname='John Deacon')
        self.project = ProjectFactory(title='Red Special', creator=self.user)

    def test_new_project_private(self):
        """Verify that a private project is not present in Solr.
        """
        docs = query(self.project.title)
        assert_equal(len(docs), 0)

    def test_make_public(self):
        """Make project public, and verify that it is present in Solr.
        """
        self.project.set_privacy('public')
        docs = query(self.project.title)
        assert_equal(len(docs), 1)

@unittest.skipIf(settings.SEARCH_ENGINE != 'elastic', 'Elastic search disabled')
class TestPublicProject(SearchTestCase):

    def setUp(self):
        self.user = UserFactory(usename='Doug Bogie')
        self.consolidate_auth = Auth(user=self.user)
        self.project = ProjectFactory(
            title='Red Special',
            creator=self.user,
            is_public=True
        )

    def test_make_private(self):
        """Make project public, then private, and verify that it is not present
        in search.
        """
        self.project.set_privacy('private')
        docs = query(self.project.title)
        assert_equal(len(docs), 0)

    def test_delete_project(self):
        """

        """
        self.project.remove_node(self.consolidate_auth)
        docs = query(self.project.title)
        assert_equal(len(docs), 0)

    def test_change_title(self):
        """

        """
        title_original = self.project.title
        self.project.set_title(
            self.project.title[::-1], self.consolidate_auth, save=True)

        docs = query(title_original)
        assert_equal(len(docs), 0)

        docs = query(self.project.title)
        assert_equal(len(docs), 1)

    def test_add_tag(self):

        tag_text = 'stonecoldcrazy'

        docs = query(tag_text)
        assert_equal(len(docs), 0)

        self.project.add_tag(tag_text, self.consolidate_auth, None)

        docs = query(tag_text)
        assert_equal(len(docs), 1)

    def test_remove_tag(self):

        tag_text = 'stonecoldcrazy'

        self.project.add_tag(tag_text, self.consolidate_auth, None)
        self.project.remove_tag(tag_text, self.consolidate_auth, None)

        docs = query(tag_text)
        assert_equal(len(docs), 0)

    def test_update_wiki(self):
        """Add text to a wiki page, then verify that project is found when
        searching for wiki text.

        """
        wiki_content = 'Hammer to fall'

        docs = query(wiki_content)
        assert_equal(len(docs), 0)

        self.project.update_node_wiki(
            'home', wiki_content, self.consolidate_auth)

        docs = query(wiki_content)
        assert_equal(len(docs), 1)

    def test_clear_wiki(self):
        """Add wiki text to page, then delete, then verify that project is not
        found when searching for wiki text.

        """
        wiki_content = 'Hammer to fall'
        self.project.update_node_wiki(
            'home', wiki_content, self.consolidate_auth)
        self.project.update_node_wiki('home', '', self.consolidate_auth)

        docs = query(wiki_content)
        assert_equal(len(docs), 0)

    def test_add_contributor(self):
        """Add a contributor, then verify that project is found when searching
        for contributor.

        """
        user2 = UserFactory(fullname='Adam Lambert')

        docs = query('"{}"'.format(user2.fullname))
        assert_equal(len(docs), 0)

        self.project.add_contributor(user2, save=True)

        docs = query('"{}"'.format(user2.fullname))
        assert_equal(len(docs), 1)

    def test_remove_contributor(self):
        """Add and remove a contributor, then verify that project is not found
        when searching for contributor.

        """
        user2 = UserFactory(fullname='Brian May')

        self.project.add_contributor(user2, save=True)
        self.project.remove_contributor(user2, self.consolidate_auth)

        docs = query('"{}"'.format(user2.fullname))
        assert_equal(len(docs), 0)

@unittest.skipIf(settings.SEARCH_ENGINE != 'elastic', 'Elastic search disabled')
class TestAddContributor(SearchTestCase):
    """Tests of the search.search_contributor method

    """

    def setUp(self):
        self.name1 = 'Roger1 Taylor1'
        self.name2 = 'John2 Deacon2'
        self.user = UserFactory(fullname=self.name1)


    def test_unreg_users_dont_show_in_search(self):
        unreg = UnregUserFactory()
        contribs = search.search_contributor(unreg.fullname)
        assert_equal(len(contribs['users']), 0)

    def test_search_fullname(self):
        """Verify that searching for full name yields exactly one result.

        """
        contribs = search.search_contributor(self.name1)
        assert_equal(len(contribs['users']), 1)

        contribs = search.search_contributor(self.name2)
        assert_equal(len(contribs['users']), 0)

    def test_search_firstname(self):
        """Verify that searching for first name yields exactly one result.

        """
        contribs = search.search_contributor(self.name1.split(' ')[0])
        assert_equal(len(contribs['users']), 1)

        contribs = search.search_contributor(self.name2.split(' ')[0])
        assert_equal(len(contribs['users']), 0)

    def test_search_partial(self):
        """Verify that searching for part of first name yields exactly one
        result.

        """
        contribs = search.search_contributor(self.name1.split(' ')[0][:-1])
        assert_equal(len(contribs['users']), 1)

        contribs = search.search_contributor(self.name2.split(' ')[0][:-1])
        assert_equal(len(contribs['users']), 0)
