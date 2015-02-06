from nose.tools import *

from tests.base import OsfTestCase


class MendeleyViewsTestCase(OsfTestCase):
    def test_user_folders(self):
        """JSON: a list of user's Mendeley folders"""
        assert_true(False)

    def test_node_mendeley_accounts(self):
        """JSON: a list of Mendeley accounts associated with the node"""
        assert_true(False)

    def test_node_citation_lists(self):
        """JSON: a list of citation lists for all associated accounts"""
        assert_true(False)

    def test_set_config_unauthorized(self):
        """Cannot associate a MendeleyAccount the user doesn't own"""
        assert_true(False)

    def test_set_config(self):
        """Settings config updates node settings"""
        assert_true(False)

    def test_set_config_node_authorized(self):
        """Can set config to an account/folder that was previous associated"""
        assert_true(False)

    def test_widget_view_complete(self):
        """JSON: everything a widget needs"""
        assert_true(False)

    def test_widget_view_incomplete(self):
        """JSON: tell the widget when it hasn't been configured"""
        assert_true(False)

    def test_citation_list(self):
        """JSON: list of formatted citations for the associated Mendeley folder
        """
        assert_true(False)

    def test_citation_list_bibtex(self):
        """JSON: list of formatted citations in BibTeX style"""
        assert_true(False)