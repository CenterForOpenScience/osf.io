# -*- coding: utf-8 -*-
from nose.tools import *  # noqa

import mock
import httpretty

from tests.base import OsfTestCase
from tests.factories import AuthUserFactory, ProjectFactory

import urlparse

from framework.auth import Auth

from website.addons.mendeley.tests.factories import (
    MendeleyAccountFactory,
    MendeleyUserSettingsFactory,
    MendeleyNodeSettingsFactory
)

from framework.exceptions import HTTPError
from website.addons.mendeley.provider import MendeleyCitationsProvider
from website.addons.mendeley.serializer import MendeleySerializer

from utils import mock_responses

API_URL = 'https://api.mendeley.com'

class MockNode(object):

    addon = None

    @property
    def is_deleted(self):
        return False

    @property
    def is_public(self):
        return True

    def get_addon(self, name):
        if name == 'mendeley':
            return self.addon
        return None

class MockFolder(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)

class MendeleyViewsTestCase(OsfTestCase):

    def setUp(self):
        super(MendeleyViewsTestCase, self).setUp()
        self.account = MendeleyAccountFactory()
        self.user = AuthUserFactory(external_accounts=[self.account])
        self.account.display_name = self.user.fullname
        self.account.save()
        self.user_addon = MendeleyUserSettingsFactory(owner=self.user, external_account=self.account)
        self.project = ProjectFactory(creator=self.user)
        self.node_addon = MendeleyNodeSettingsFactory(owner=self.project)
        self.node_addon.set_auth(external_account=self.account, user=self.user)
        self.provider = MendeleyCitationsProvider()
        #self.user_addon.grant_oauth_access(self.node_addon, self.account, metadata={'lists': 'list'})
        self.node = MockNode()
        self.node.addon = self.node_addon
        self.id_patcher = mock.patch('website.addons.mendeley.model.Mendeley.client_id')
        self.secret_patcher = mock.patch('website.addons.mendeley.model.Mendeley.client_secret')
        self.id_patcher.__get__ = mock.Mock(return_value='1234567890asdf')
        self.secret_patcher.__get__ = mock.Mock(return_value='1234567890asdf')
        self.id_patcher.start()
        self.secret_patcher.start()

    def tearDown(self):
        self.id_patcher.stop()
        self.secret_patcher.stop()

    @mock.patch('website.addons.mendeley.model.Mendeley.client', new_callable=mock.PropertyMock)
    def test_check_mendeley_credentials(self, mock_client):
        mock_client.side_effect = HTTPError(403)
        assert_false(self.provider.check_credentials(self.node_addon))

        mock_client.side_effect = HTTPError(402)
        with assert_raises(HTTPError):
            self.provider.check_credentials(self.node_addon)

    @mock.patch('website.addons.mendeley.views.MendeleyCitationsProvider.check_credentials')
    def test_serialize_settings_authorizer(self, mock_credentials):
        #"""dict: a serialized version of user-specific addon settings"""
        mock_credentials.return_value = True
        res = self.app.get(
            self.project.api_url_for('mendeley_get_config'),
            auth=self.user.auth,
        )
        result = res.json['result']
        assert_true(result['nodeHasAuth'])
        assert_true(result['userHasAuth'])
        assert_true(result['userIsOwner'])
        assert_true(result['validCredentials'])
        assert_equal(result['folder'], {'name': ''})
        assert_equal(result['ownerName'], self.user.fullname)
        assert_true(result['urls']['auth'])
        assert_true(result['urls']['config'])
        assert_true(result['urls']['deauthorize'])
        assert_true(result['urls']['folders'])
        assert_true(result['urls']['importAuth'])
        assert_true(result['urls']['settings'])

    @mock.patch('website.addons.mendeley.views.MendeleyCitationsProvider.check_credentials')
    def test_serialize_settings_non_authorizer(self, mock_credentials):
        #"""dict: a serialized version of user-specific addon settings"""
        mock_credentials.return_value = True
        non_authorizing_user = AuthUserFactory()
        self.project.add_contributor(non_authorizing_user, save=True)
        res = self.app.get(
            self.project.api_url_for('mendeley_get_config'),
            auth=non_authorizing_user.auth,
        )
        result = res.json['result']
        assert_true(result['nodeHasAuth'])
        assert_false(result['userHasAuth'])
        assert_false(result['userIsOwner'])
        assert_true(result['validCredentials'])
        assert_equal(result['folder'], {'name': ''})
        assert_equal(result['ownerName'], self.user.fullname)
        assert_true(result['urls']['auth'])
        assert_true(result['urls']['config'])
        assert_true(result['urls']['deauthorize'])
        assert_true(result['urls']['folders'])
        assert_true(result['urls']['importAuth'])
        assert_true(result['urls']['settings'])

    @mock.patch('website.addons.mendeley.provider.MendeleyCitationsProvider.check_credentials')
    def test_set_auth(self, mock_credentials):

        mock_credentials.return_value = True
        res = self.app.put_json(
            self.project.api_url_for('mendeley_add_user_auth'),
            {
                'external_account_id': self.account._id,
            },
            auth=self.user.auth,
        )

        assert_equal(
            res.status_code,
            200
        )

        assert_true(res.json['result']['userHasAuth'])

        assert_equal(
            self.node_addon.user_settings,
            self.user_addon
        )
        assert_equal(
            self.node_addon.external_account,
            self.account
        )

    def test_remove_user_auth(self):
        self.node_addon.set_auth(self.account, self.user)

        res = self.app.delete_json(
            self.project.api_url_for('mendeley_remove_user_auth'),
            {
                'external_account_id': self.account._id,
            },
            auth=self.user.auth,
        )

        assert_equal(
            res.status_code,
            200
        )

        self.node_addon.reload()

        assert_is_none(self.node_addon.user_settings)
        assert_is_none(self.node_addon.external_account)

    @mock.patch('website.addons.mendeley.model.Mendeley._folder_metadata')
    def test_set_config_owner(self, mock_metadata):
        mock_metadata.return_value = MockFolder(name='Fake Folder')
        # Settings config updates node settings
        self.node_addon.associated_user_settings = []
        self.node_addon.save()
        res = self.app.put_json(
            self.project.api_url_for('mendeley_set_config'),
            {
                'external_account_id': self.account._id,
                'external_list_id': 'list',
            },
            auth=self.user.auth,
        )
        self.node_addon.reload()
        assert_equal(self.user_addon, self.node_addon.user_settings)
        serializer = MendeleySerializer(node_settings=self.node_addon, user_settings=self.user_addon)
        expected = {
            'result': serializer.serialized_node_settings
        }
        assert_equal(res.json, expected)

    @mock.patch('website.addons.mendeley.model.Mendeley._folder_metadata')
    def test_set_config_not_owner(self, mock_metadata):
        mock_metadata.return_value = MockFolder(name='Fake Folder')
        user = AuthUserFactory()
        user.add_addon('mendeley')
        self.project.add_contributor(user)
        self.project.save()
        res = self.app.put_json(
            self.project.api_url_for('mendeley_set_config'),
            {
                'external_account_id': self.account._id,
                'external_list_id': 'list',
            },
            auth=user.auth,
        )
        self.node_addon.reload()
        assert_equal(self.user_addon, self.node_addon.user_settings)
        serializer = MendeleySerializer(node_settings=self.node_addon, user_settings=None)
        expected = {
            'result': serializer.serialized_node_settings
        }
        assert_equal(res.json, expected)

    def test_mendeley_widget_view_complete(self):
        # JSON: everything a widget needs
        assert_false(self.node_addon.complete)
        assert_equal(self.node_addon.mendeley_list_id, None)
        self.node_addon.set_target_folder('ROOT-ID', 'ROOT', auth=Auth(user=self.user))
        url = self.project.api_url_for('mendeley_widget')
        res = self.app.get(url, auth=self.user.auth).json

        assert_true(res['complete'])
        assert_equal(res['list_id'], 'ROOT-ID')

    def test_widget_view_incomplete(self):
        # JSON: tell the widget when it hasn't been configured
        assert_false(self.node_addon.complete)
        assert_equal(self.node_addon.mendeley_list_id, None)
        url = self.project.api_url_for('mendeley_widget')
        res = self.app.get(url, auth=self.user.auth).json

        assert_false(res['complete'])
        assert_is_none(res['list_id'])

    @httpretty.activate
    def test_mendeley_citation_list_root(self):

        httpretty.register_uri(
            httpretty.GET,
            urlparse.urljoin(API_URL, 'folders'),
            body=mock_responses['folders'],
            content_type='application/json'
        )

        res = self.app.get(
            self.project.api_url_for('mendeley_citation_list'),
            auth=self.user.auth
        )
        root = res.json['contents'][0]
        assert_equal(root['kind'], 'folder')
        assert_equal(root['id'], 'ROOT')
        assert_equal(root['parent_list_id'], '__')

    @httpretty.activate
    def test_mendeley_citation_list_non_root(self):

        httpretty.register_uri(
            httpretty.GET,
            urlparse.urljoin(API_URL, 'folders'),
            body=mock_responses['folders'],
            content_type='application/json'
        )

        httpretty.register_uri(
            httpretty.GET,
            urlparse.urljoin(API_URL, 'documents'),
            body=mock_responses['documents'],
            content_type='application/json'
        )

        res = self.app.get(
            self.project.api_url_for('mendeley_citation_list', mendeley_list_id='ROOT'),
            auth=self.user.auth
        )

        children = res.json['contents']
        assert_equal(len(children), 7)
        assert_equal(children[0]['kind'], 'folder')
        assert_equal(children[1]['kind'], 'file')
        assert_true(children[1].get('csl') is not None)

    @httpretty.activate
    def test_mendeley_citation_list_non_linked_or_child_non_authorizer(self):

        non_authorizing_user = AuthUserFactory()
        self.project.add_contributor(non_authorizing_user, save=True)

        self.node_addon.mendeley_list_id = 'e843da05-8818-47c2-8c37-41eebfc4fe3f'
        self.node_addon.save()

        httpretty.register_uri(
            httpretty.GET,
            urlparse.urljoin(API_URL, 'folders'),
            body=mock_responses['folders'],
            content_type='application/json'
        )

        httpretty.register_uri(
            httpretty.GET,
            urlparse.urljoin(API_URL, 'documents'),
            body=mock_responses['documents'],
            content_type='application/json'
        )

        res = self.app.get(
            self.project.api_url_for('mendeley_citation_list', mendeley_list_id='ROOT'),
            auth=non_authorizing_user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 403)
