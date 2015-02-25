# -*- coding: utf-8 -*-

from nose.tools import *  # noqa

import responses
import mock
import unittest

from tests.base import OsfTestCase
from tests.factories import AuthUserFactory, ProjectFactory

import json
import urlparse

from website.addons.zotero.tests.factories import (
    ZoteroAccountFactory, ZoteroUserSettingsFactory,
    ZoteroNodeSettingsFactory
)

from website.util import api_url_for
from website.addons.zotero import views
from website.addons.citations.utils import serialize_account

from utils import mock_responses

API_URL = 'https://api.zotero.org'

class MockNode(object):

    addon = None

    @property
    def is_deleted(self):
        return False

    @property
    def is_public(self):
        return True

    def get_addon(self, name):
        if name == 'zotero':
            return self.addon
        return None


class ZoteroViewsTestCase(OsfTestCase):

    def setUp(self):
        super(ZoteroViewsTestCase, self).setUp()
        self.account = ZoteroAccountFactory()
        self.user = AuthUserFactory(external_accounts=[self.account])
        self.account.display_name = self.user.fullname
        self.account.save()
        self.user_addon = ZoteroUserSettingsFactory(owner=self.user, external_account=self.account)
        self.project = ProjectFactory(creator=self.user)
        self.node_addon = ZoteroNodeSettingsFactory(owner=self.project)
        self.node_addon.set_auth(external_account=self.account, user=self.user)
        #self.user_addon.grant_oauth_access(self.node_addon, self.account, metadata={'lists': 'list'})
        self.node = MockNode()
        self.node.addon = self.node_addon
        self.id_patcher = mock.patch('website.addons.zotero.model.Zotero.client_id')
        self.secret_patcher = mock.patch('website.addons.zotero.model.Zotero.client_secret')
        self.id_patcher.__get__ = mock.Mock(return_value='1234567890asdf')
        self.secret_patcher.__get__ = mock.Mock(return_value='1234567890asdf')
        self.id_patcher.start()
        self.secret_patcher.start()

    def tearDown(self):
        self.id_patcher.stop()
        self.secret_patcher.stop()

    def test_serialize_settings_authorizer(self):
        #"""dict: a serialized version of user-specific addon settings"""
        res = self.app.get(
            self.project.api_url_for('zotero_get_config'),
            auth=self.user.auth,
        )
        assert_true(res.json['nodeHasAuth'])
        assert_true(res.json['userHasAuth'])
        assert_true(res.json['userIsOwner'])
        assert_equal(res.json['folder'], '')
        assert_equal(res.json['ownerName'], self.user.fullname)
        assert_true(res.json['urls']['auth'])
        assert_true(res.json['urls']['config'])
        assert_true(res.json['urls']['deauthorize'])
        assert_true(res.json['urls']['folders'])
        assert_true(res.json['urls']['importAuth'])
        assert_true(res.json['urls']['settings'])

    def test_serialize_settings_non_authorizer(self):
        #"""dict: a serialized version of user-specific addon settings"""
        non_authorizing_user = AuthUserFactory()
        self.project.add_contributor(non_authorizing_user, save=True)
        res = self.app.get(
            self.project.api_url_for('zotero_get_config'),
            auth=non_authorizing_user.auth,
        )
        assert_true(res.json['nodeHasAuth'])
        assert_false(res.json['userHasAuth'])
        assert_false(res.json['userIsOwner'])
        assert_equal(res.json['folder'], '')
        assert_equal(res.json['ownerName'], self.user.fullname)
        assert_true(res.json['urls']['auth'])
        assert_true(res.json['urls']['config'])
        assert_true(res.json['urls']['deauthorize'])
        assert_true(res.json['urls']['folders'])
        assert_true(res.json['urls']['importAuth'])
        assert_true(res.json['urls']['settings'])

    def test_user_folders(self):
        # JSON: a list of user's Zotero folders"
        res = self.app.get(
            api_url_for('list_zotero_accounts_user'),
            auth=self.user.auth,
        )
        expected = {
            'accounts': [
                serialize_account(each)
                for each in self.user.external_accounts
                if each.provider == 'zotero'
            ]
        }
        assert_equal(res.json, expected)

    def test_set_auth(self):

        res = self.app.post_json(
            self.project.api_url_for('zotero_add_user_auth'),
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
        self.node_addon.save()

        res = self.app.delete_json(
            self.project.api_url_for('zotero_remove_user_auth'),
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

    def test_set_config_owner(self):
        # Settings config updates node settings
        self.node_addon.associated_user_settings = []
        self.node_addon.save()
        res = self.app.put_json(
            self.project.api_url_for('zotero_set_config'),
            {
                'external_account_id': self.account._id,
                'external_list_id': 'list',
            },
            auth=self.user.auth,
        )
        self.node_addon.reload()
        assert_equal(self.user_addon, self.node_addon.user_settings)
        assert_equal(res.json, {})

    def test_set_config_not_owner(self):
        user = AuthUserFactory()
        user.add_addon('zotero')
        self.project.add_contributor(user)
        self.project.save()
        res = self.app.put_json(
            self.project.api_url_for('zotero_set_config'),
            {
                'external_account_id': self.account._id,
                'external_list_id': 'list',
            },
            auth=user.auth,
        )
        self.node_addon.reload()
        assert_equal(self.user_addon, self.node_addon.user_settings)
        assert_equal(res.json, {})

    def test_zotero_widget_view_complete(self):
        # JSON: everything a widget needs
        assert_false(self.node_addon.complete)
        assert_equal(self.node_addon.zotero_list_id, None)
        self.node_addon.set_target_folder('ROOT')
        res = views.zotero_widget(node_addon=self.node_addon,
                                    project=self.project,
                                    node=self.node,
                                    nid=self.node_addon._id,
                                    pid=self.project._id,
                                    auth=self.user.auth)
        assert_true(res['complete'])
        assert_equal(res['list_id'], 'ROOT')

    def test_widget_view_incomplete(self):
        # JSON: tell the widget when it hasn't been configured
        assert_false(self.node_addon.complete)
        assert_equal(self.node_addon.zotero_list_id, None)
        res = views.zotero_widget(node_addon=self.node_addon,
                                    project=self.project,
                                    node=self.node,
                                    nid=self.node_addon._id,
                                    pid=self.project._id,
                                    auth=self.user.auth)
        assert_false(res['complete'])
        assert_is_none(res['list_id'])

    @responses.activate
    def test_zotero_citation_list_root(self):

        responses.add(
            responses.GET,
            urlparse.urljoin(
                API_URL,
                'users/{}/collections'.format(self.account.provider_id)
            ),
            body=mock_responses['folders'],
            content_type='application/json'
        )

        res = self.app.get(
            self.project.api_url_for('zotero_citation_list'),
            auth=self.user.auth
        )
        root = res.json['contents'][0]
        assert_equal(root['kind'], 'folder')
        assert_equal(root['id'], 'ROOT')
        assert_equal(root['parent_list_id'], '__')

    @responses.activate
    def test_zotero_citation_list_non_root(self):

        responses.add(
            responses.GET,
            urlparse.urljoin(
                API_URL,
                'users/{}/collections'.format(self.account.provider_id)
            ),
            body=mock_responses['folders'],
            content_type='application/json'
        )

        responses.add(
            responses.GET,
            urlparse.urljoin(
                API_URL,
                'users/{}/items'.format(self.account.provider_id)
            ),
            body=mock_responses['documents'],
            content_type='application/json'
        )

        res = self.app.get(
            self.project.api_url_for('zotero_citation_list', zotero_list_id='ROOT'),
            auth=self.user.auth
        )

        children = res.json['contents']
        assert_equal(len(children), 7)
        assert_equal(children[0]['kind'], 'folder')
        assert_equal(children[1]['kind'], 'file')
        assert_true(children[1].get('csl') is not None)

    @responses.activate
    def test_zotero_citation_list_non_linked_or_child_non_authorizer(self):

        non_authorizing_user = AuthUserFactory()
        self.project.add_contributor(non_authorizing_user, save=True)

        self.node_addon.zotero_list_id = 'e843da05-8818-47c2-8c37-41eebfc4fe3f'
        self.node_addon.save()

        responses.add(
            responses.GET,
            urlparse.urljoin(
                API_URL,
                'users/{}/collections'.format(self.account.provider_id)
            ),
            body=mock_responses['folders'],
            content_type='application/json'
        )

        responses.add(
            responses.GET,
            urlparse.urljoin(
                API_URL,
                'users/{}/items'.format(self.account.provider_id)
            ),
            body=mock_responses['documents'],
            content_type='application/json'
        )

        res = self.app.get(
            self.project.api_url_for('zotero_citation_list', zotero_list_id='ROOT'),
            auth=non_authorizing_user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 403)
