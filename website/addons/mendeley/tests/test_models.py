# -*- coding: utf-8 -*-

import mock
from nose.tools import *  # noqa

from tests.base import OsfTestCase
from tests.factories import UserFactory, ProjectFactory
from website.addons.mendeley.tests.factories import (
    MendeleyAccountFactory, MendeleyUserSettingsFactory,
    MendeleyNodeSettingsFactory
)

import datetime

from website.addons.mendeley import model

class MockFolder(object):
    
    @property
    def name(self):
        return 'somename'

    @property
    def json(self):
        return {'id': 'abc123', 'parent_id': 'cba321'}


class MendeleyProviderTestCase(OsfTestCase):

    def setUp(self):
        super(MendeleyProviderTestCase, self).setUp()
        self.provider = model.Mendeley()

    @mock.patch('website.addons.mendeley.model.Mendeley._get_client')
    def test_handle_callback(self, mock_get_client):
        """Must return provider_id and display_name"""
        mock_client = mock.Mock()
        mock_client.profiles.me = mock.Mock(id='testid', display_name='testdisplay')
        mock_get_client.return_value = mock_client
        res = self.provider.handle_callback('testresponse')
        mock_get_client.assert_called_with('testresponse')
        assert_equal(res.get('provider_id'), 'testid')
        assert_equal(res.get('display_name'), 'testdisplay')

    @mock.patch('website.addons.mendeley.model.Mendeley._get_client')
    def test_client_not_cached(self, mock_get_client):
        """The first call to .client returns a new client"""
        mock_account = mock.Mock()
        mock_account.expires_at = datetime.datetime.now()
        self.provider.account = mock_account
        self.provider.client
        mock_get_client.assert_called
        assert_true(mock_get_client.called)

    @mock.patch('website.addons.mendeley.model.Mendeley._get_client')
    def test_client_cached(self, mock_get_client):
        """Repeated calls to .client returns the same client"""
        self.provider._client = mock.Mock()
        res = self.provider.client
        assert_equal(res, self.provider._client)
        assert_false(mock_get_client.called)

    def test_citation_lists(self):
        mock_client = mock.Mock()
        mock_folders = [MockFolder()]
        mock_list = mock.Mock()
        mock_list.items = mock_folders
        mock_client.folders.list.return_value = mock_list
        self.provider._client = mock_client
        mock_account = mock.Mock()
        self.provider.account = mock_account
        res = self.provider.citation_lists
        assert_equal(res[1]['name'], mock_folders[0].name)
        assert_equal(res[1]['id'], mock_folders[0].json['id'])

#    @mock.patch('website.addons.mendeley.model.Mendeley._citations_for_mendeley_user')
#    @mock.patch('website.addons.mendeley.model.Mendeley._citations_for_mendeley_folder')
#    def test_get_citation_list_folder(self, mock_folder_citations, mock_user_citations):
#        mock_client = mock.Mock()
#        mock_folder = mock.Mock()
#        mock_folder.name = 'folder'
#        mock_client.folders = {'folder': mock_folder}
#        self.provider._client = mock_client
#        mock_account = mock.Mock()
#        self.provider.account = mock_account
#        res = self.provider.get_list('folder')
#        assert_true(isinstance(res, set))
#        assert_equal(res.name, 'folder')
#        assert_equal(res.provider_account_id, mock_account.provider_id)
#        assert_equal(res.provider_list_id, 'folder')
#        res.citations
#        mock_folder_citations.assert_called_with(mock_folder)
#        assert_false(mock_user_citations.called)
# # These two have 'res' returned as a MagicMock. Assuming this is unintended
#    @mock.patch('website.addons.mendeley.model.Mendeley._citations_for_mendeley_user')
#    @mock.patch('website.addons.mendeley.model.Mendeley._citations_for_mendeley_folder')
#    def test_get_citation_list_no_folder(self, mock_folder_citations, mock_user_citations):
#        mock_client = mock.Mock()
#        mock_client.folders = {}
#        self.provider._client = mock_client
#        mock_account = mock.Mock()
#        mock_account.display_name = 'name'
#        self.provider.account = mock_account
#        res = self.provider.get_list('folder')
#        assert_true(isinstance(res, set))
#        assert_equal(res.name, 'name')
#        assert_equal(res.provider_account_id, mock_account.provider_id)
#        assert_equal(res.provider_list_id, 'folder')
#        res.citations
#        mock_user_citations.assert_called()
#        assert_false(mock_folder_citations.called)


class MendeleyNodeSettingsTestCase(OsfTestCase):

    def setUp(self):
        super(MendeleyNodeSettingsTestCase, self).setUp()
        self.node_addon = model.AddonMendeleyNodeSettings()
        self.node_addon.save()

    @mock.patch('website.addons.mendeley.model.Mendeley')
    def test_api_not_cached(self, mock_mendeley):
        """The first call to .api returns a new object"""
        api = self.node_addon.api
        mock_mendeley.assert_called_once()
        assert_equal(api, mock_mendeley())

    @mock.patch('website.addons.mendeley.model.Mendeley')
    def test_api_cached(self, mock_mendeley):
        """Repeated calls to .api returns the same object"""
        self.node_addon._api = 'testapi'
        api = self.node_addon.api
        assert_false(mock_mendeley.called)
        assert_equal(api, 'testapi')

# "Ignore oauth for now?" (-Lyndsy)
#    def test_grant_oauth(self):
#        """Grant the node access to a single folder in a Mendeley account"""
#        account = MendeleyAccountFactory()
#        user_addon = MendeleyUserSettingsFactory()
#        node_addon = MendeleyNodeSettingsFactory()
#        node_addon.grant_oauth_access(user_addon.owner, account, metadata=None)
#        assert_in(user_addon, node_addon.associated_user_settings)
#        assert_equal(user_addon.oauth_grants[node_addon.owner._id][account._id], None)

    def test_verify_oauth_current_user(self):
        """Confirm access to a Mendeley account attached to the current user"""
        account = MendeleyAccountFactory()
        user = UserFactory()
        user_addon = MendeleyUserSettingsFactory(owner=user)
        node_addon = MendeleyNodeSettingsFactory(owner=ProjectFactory(creator=user))
        node_addon.grant_oauth_access(user_addon.owner, account, metadata={'lists': 'testlist'})
        assert_true(node_addon.verify_oauth_access(account, 'testlist'))

    def test_verify_oauth_other_user(self):
        """Verify access to a Mendeley account's folder beloning to another user
        """
        account = MendeleyAccountFactory()
        user_addon = MendeleyUserSettingsFactory()
        node_addon = MendeleyNodeSettingsFactory()
        node_addon.grant_oauth_access(user_addon.owner, account, metadata={'lists': 'testlist'})
        assert_true(node_addon.verify_oauth_access(account, 'testlist'))

    def test_verify_oauth_other_user_failed(self):
        """Verify access to a Mendeley account's folder where the account is
        associated with the node, but the folder is not
        """
        account = MendeleyAccountFactory()
        user = UserFactory()
        user_addon = MendeleyUserSettingsFactory(owner=user)
        node_addon = MendeleyNodeSettingsFactory(owner=ProjectFactory(creator=user))
        node_addon.grant_oauth_access(user_addon.owner, account, metadata={'lists': 'testlist'})
        assert_false(node_addon.verify_oauth_access(account, 'privatelist'))

    def test_to_json(self):
        """All values are passed to the node settings view"""
        user_account = MendeleyAccountFactory()
        user = UserFactory(external_accounts=[user_account])
        node_account = MendeleyAccountFactory()
        node_addon = MendeleyNodeSettingsFactory(external_account=node_account)
        res = node_addon.to_json(user)
        assert_equal(len(res['accounts']), 2)
        for account in [user_account, node_account]:
            assert_in(
                {
                    'id': account._id,
                    'provider_id': account.provider_id,
                    'display_name': account.display_name
                },
                res['accounts'],
            )


class MendeleyUserSettingsTestCase(OsfTestCase):
    def test_get_connected_accounts(self):
        """Get all Mendeley accounts for user"""
        user_accounts = [MendeleyAccountFactory(), MendeleyAccountFactory()]
        user = UserFactory(external_accounts=user_accounts)
        user_addon = MendeleyUserSettingsFactory(owner=user)
        assert_equal(user_addon._get_connected_accounts(), user_accounts)

    def test_to_json(self):
        """All values are passed to the user settings view"""
        user_accounts = [MendeleyAccountFactory(), MendeleyAccountFactory()]
        user = UserFactory(external_accounts=user_accounts)
        user_addon = MendeleyUserSettingsFactory(owner=user)
        res = user_addon.to_json(user)
        for account in user_accounts:
            assert_in(
                {
                    'id': account._id,
                    'provider_id': account.provider_id,
                    'display_name': account.display_name
                },
                res['accounts'],
            )
