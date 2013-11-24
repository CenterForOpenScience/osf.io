import unittest
from nose.tools import *  # PEP8 asserts

from tests.base import DbTestCase
from tests.factories import UserFactory, ProjectFactory, TagFactory

from framework.search.solr import solr
from framework.search.utils import clean_solr_doc
from website.search.solr_search import search_solr

class TestCleanSolr(unittest.TestCase):

    def test_clean_string(self):
        dirty_string = u'roger\x0btaylor'
        assert_equal(
            clean_solr_doc(dirty_string),
            'rogertaylor'
        )

    def test_clean_list(self):
        dirty_strings = [
            u'slightly\x0bmad',
            [
                u'banana\x0ctree',
            ]
        ]
        assert_equal(
            clean_solr_doc(dirty_strings),
            [
                'slightlymad',
                [
                    'bananatree',
                ]
            ]
        )

    def test_clean_dict(self):
        dirty_strings = {
            'bass': u'john\x0bdeacon',
            'guitar' : {
                'brian': u'may\x0b',
            },
        }
        assert_equal(
            clean_solr_doc(dirty_strings),
            {
                'bass': 'johndeacon',
                'guitar': {
                    'brian': 'may',
                }
            }
        )


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

        docs = query(tag_text)
        assert_equal(len(docs), 0)

        self.project.add_tag(tag_text, self.user, None)

        docs = query(tag_text)
        assert_equal(len(docs), 1)

    def test_remove_tag(self):

        tag_text = 'stonecoldcrazy'

        self.project.add_tag(tag_text, self.user, None)
        self.project.remove_tag(tag_text, self.user, None)

        docs = query(tag_text)
        assert_equal(len(docs), 0)

    def test_update_wiki(self):
        """Add text to a wiki page, then verify that project is found when
        searching for wiki text.

        """
        wiki_content = 'Hammer to fall'

        docs = query(wiki_content)
        assert_equal(len(docs), 0)

        self.project.update_node_wiki('home', wiki_content, self.user, None)

        docs = query(wiki_content)
        assert_equal(len(docs), 1)

    def test_clear_wiki(self):
        """Add wiki text to page, then delete, then verify that project is not
        found when searching for wiki text.

        """
        wiki_content = 'Hammer to fall'
        self.project.update_node_wiki('home', wiki_content, self.user, None)
        self.project.update_node_wiki('home', '', self.user, None)

        docs = query(wiki_content)
        assert_equal(len(docs), 0)


    def test_add_contributor(self):
        """Add a contributor, then verify that project is found when searching
        for contributor.

        """
        user2 = UserFactory()

        docs = query(user2.fullname)
        assert_equal(len(docs), 0)

        self.project.add_contributor(user2, save=True)

        docs = query(user2.fullname)
        assert_equal(len(docs), 1)

    def test_remove_contributor(self):
        """Add and remove a contributor, then verify that project is not found
        when searching for contributor.

        """
        user2 = UserFactory()

        self.project.add_contributor(user2, save=True)
        self.project.remove_contributor(user2, self.user)

        docs = query(user2.fullname)
        assert_equal(len(docs), 0)
