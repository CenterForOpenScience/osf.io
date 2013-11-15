from nose.tools import *  # PEP8 asserts

from tests.base import DbTestCase
from tests.factories import UserFactory

from framework.search.solr import solr
from website.search.solr_search import search_solr

class SolrTestCase(DbTestCase):

    def tearDown(self):
        solr.delete_all()
        solr.commit()

def _query_user(fullname):
    query = 'user:"{}"'.format(fullname)
    results, _, _ = search_solr(query)
    return results.get('docs', [])

class TestUserUpdate(SolrTestCase):

    def test_new_user(self):
        """Add a user, then verify that user is present in Solr.

        """
        # Create user
        user = UserFactory()

        # Verify that user has been added to Solr
        docs = _query_user(user.fullname)
        assert_equal(len(docs), 1)

    def test_change_name(self):
        """Add a user, change her name, and verify that only the new name is
        found in Solr.

        """
        user = UserFactory()
        fullname_original = user.fullname
        user.fullname = user.fullname[::-1]
        user.save()

        docs_original = _query_user(fullname_original)
        assert_equal(len(docs_original), 0)

        docs_current = _query_user(user.fullname)
        assert_equal(len(docs_current), 1)

class TestNodeUpdate(SolrTestCase):

    def test_new_node_private(self):
        pass

    def test_make_public(self):
        pass

    def test_make_private(self):
        pass

    def test_delete_node(self):
        pass

    def test_change_title(self):
        pass

    def test_update_wiki(self):
        pass

    def test_add_contributor(self):
        pass

    def test_remove_contributor(self):
        pass
