from nose.tools import *

from tests.base import OsfTestCase


class MendeleyProviderTestCase(OsfTestCase):
    def test_handle_callback(self):
        """Must return provider_id and display_name"""
        assert_true(False)

    def test_client_not_cached(self):
        """The first call to .client returns a new client"""
        assert_true(False)

    def test_client_cached(self):
        """Repeated calls to .client returns the same client"""
        assert_true(False)

    def test_citation_lists(self):
        """Get a list of Mendeley folders as CitationList instances

        Must also contain a CitationList to represent the account itself
        """
        assert_true(False)

    def test_get_citation_list(self):
        """Get a single MendeleyList as a CitationList, inluding Citations"""
        assert_true(False)


class MendeleyNodeSettingsTestCase(OsfTestCase):
    def test_api_not_cached(self):
        """The first call to .api returns a new object"""
        assert_true(False)

    def test_api_cached(self):
        """Repeated calls to .api returns the same object"""
        assert_true(False)

    def test_grant_oauth(self):
        """Grant the node access to a single folder in a Mendeley account"""
        assert_true(False)

    def test_revoke_oauth(self):
        """Revoke access to a Mendeley account for the node"""
        assert_true(False)

    def test_verify_oauth_current_user(self):
        """Confirm access to a Mendeley account attached to the current user"""
        assert_true(False)

    def test_verify_oauth_other_user(self):
        """Verify access to a Mendeley account's folder beloning to another user
        """
        assert_true(False)

    def test_verify_oauth_other_user_failed(self):
        """Verify access to a Mendeley account's folder where the account is
        associated with the node, but the folder is not
        """
        assert_true(False)

    def test_verify_json(self):
        """All values are passed to the node settings view"""
        assert_true(False)


class MendeleyUserSettingsTestCase(OsfTestCase):
    def test_get_connected_accounts(self):
        """Get all Mendeley accounts for user"""
        assert_true(False)

    def test_to_json(self):
        """All values are passed to the user settings view"""
        assert_true(False)
