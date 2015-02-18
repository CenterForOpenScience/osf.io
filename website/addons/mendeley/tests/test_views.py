# -*- coding: utf-8 -*-

from nose.tools import *  # noqa

import responses

from tests.base import OsfTestCase
from tests.factories import AuthUserFactory, ProjectFactory

import json
import urlparse

from website.addons.mendeley.tests.factories import (
    MendeleyAccountFactory, MendeleyUserSettingsFactory,
    MendeleyNodeSettingsFactory
)

from website.util import api_url_for
from website.addons.mendeley import utils
from website.addons.mendeley.views import serialize_settings, serialize_urls

from utils import mock_responses

API_URL = 'https://api.mendeley.com'

class MendeleyViewsTestCase(OsfTestCase):

    def setUp(self):
        super(MendeleyViewsTestCase, self).setUp()
        self.account = MendeleyAccountFactory()
        self.user = AuthUserFactory(external_accounts=[self.account])
        self.account.display_name = self.user.fullname
        self.account.save()
        self.user_addon = MendeleyUserSettingsFactory(owner=self.user)
        self.project = ProjectFactory(creator=self.user)
        self.node_addon = MendeleyNodeSettingsFactory(owner=self.project, external_account=self.account)
        self.node_addon.grant_oauth_access(self.user, self.account, metadata={'lists': 'list'})


    def test_serialize_settings_authorizer(self):
        #"""dict: a serialized version of user-specific addon settings"""
        res = serialize_settings(self.node_addon, self.user)
        expected = {
            'nodeHasAuth': True,
            'userIsOwner': True,
            'userHasAuth': True,
            'urls': serialize_urls(self.node_addon),
            'userAccountId': filter(lambda a: a.provider == 'mendeley', self.user.external_accounts)[0]._id,
            'folder': '',
            'ownerName': self.user.fullname            
        }
        assert_dict_equal(res, expected)
        

    def test_serialize_settings_non_authorizer(self):
        #"""dict: a serialized version of user-specific addon settings"""
        non_authorizing_user = AuthUserFactory()
        self.project.add_contributor(non_authorizing_user, save=True)    
        res = serialize_settings(self.node_addon, non_authorizing_user)
        expected = {
            'nodeHasAuth': True,
            'userIsOwner': False,
            'userHasAuth': False,
            'urls': serialize_urls(self.node_addon),
            'userAccountId': None,
            'folder': '',
            'ownerName': self.user.fullname            
        }
        assert_dict_equal(res, expected)
        

    def test_user_folders(self):
        """JSON: a list of user's Mendeley folders"""
        res = self.app.get(
            api_url_for('list_mendeley_accounts_user'),
            auth=self.user.auth,
        )
        expected = {
            'accounts': [
                utils.serialize_account(each)
                for each in self.user.external_accounts
                if each.provider == 'mendeley'
            ]
        }
        assert_equal(res.json, expected)

    '''
    TODO delete?
    def test_node_mendeley_accounts(self):
        """JSON: a list of Mendeley accounts associated with the node"""
        res = self.app.get(
            self.project.api_url_for('list_mendeley_accounts_node'),
            auth=self.user.auth
        )
        import ipdb; ipdb.set_trace()
        expected = {
            'accounts': [
                utils.serialize_account(each)
                for each in self.node_addon.get_accounts(self.user)
            ]
        }
        assert_equal(res.json, expected)
    '''

    @responses.activate
    def test_node_citation_lists(self):
        """JSON: a list of citation lists for all associated accounts"""
        responses.add(
            responses.GET,
            urlparse.urljoin(API_URL, 'folders'),
            body=mock_responses['folders'],
            content_type='application/json',
        )
        
        res = self.app.get(
            self.project.api_url_for('list_citationlists_node', account_id=self.account._id),
            auth=self.user.auth,
        )
        lists = [each for each in self.node_addon.api.citation_lists]
        assert_dict_equal(
            res.json,
            {
                'citation_lists': lists
            }
        )

    def test_node_citation_lists_not_found(self):
        """JSON: a list of citation lists for all associated accounts"""
        res = self.app.get(
            self.project.api_url_for('list_citationlists_node', account_id=self.account._id[::-1]),
            auth=self.user.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, 404)

    def test_set_config_unauthorized(self):
        """Cannot associate a MendeleyAccount the user doesn't own"""
        account = MendeleyAccountFactory()
        res = self.app.put_json(
            self.project.api_url_for('mendeley_set_config'),
            {
                'external_account_id': account._id,
                'external_list_id': 'private',
            },
            auth=self.user.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, 403)

    def test_set_config_owner(self):
        """Settings config updates node settings"""
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
        assert_in(self.user_addon, self.node_addon.associated_user_settings)
        assert_equal(res.json, {})

    def test_set_config_not_owner(self):
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
        assert_in(self.user_addon, self.node_addon.associated_user_settings)
        assert_equal(res.json, {})

    def test_set_config_node_authorized(self):
        """Can set config to an account/folder that was previous associated"""
        pass

        

    def test_mendeley_widget_view_complete(self):
        """JSON: everything a widget needs"""

        self.node_addon.mendeley_list_id = 'ROOT'
        self.node_addon.save()
        
        res = self.app.get(
            self.project.api_url_for('mendeley_widget'),
            auth=self.user.auth
        )
        assert_equal(res.json['complete'], 'ROOT')
        

    def test_mendeley_widget_view_incomplete(self):
        #"""JSON: tell the widget when it hasn't been configured"""

        res = self.app.get(
            self.project.api_url_for('mendeley_widget'),
            auth=self.user.auth
        )        
        assert_is_none(res.json['complete'])
            
    
    @responses.activate
    def test_mendeley_citation_list_root(self):

        responses.add(
            responses.GET,
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

    @responses.activate
    def test_mendeley_citation_list_non_root(self):

        responses.add(
            responses.GET,
            urlparse.urljoin(API_URL, 'folders'),
            body=mock_responses['folders'],
            content_type='application/json'
        )

        responses.add(
            responses.GET,
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
        assert_equal(children[1]['kind'], 'item')
        assert_true(children[1].get('csl') is not None)

    @responses.activate
    def test_mendeley_citation_list_non_linked_or_child_non_authorizer(self):

        non_authorizing_user = AuthUserFactory()
        self.project.add_contributor(non_authorizing_user, save=True)
        
        self.node_addon.mendeley_list_id = 'e843da05-8818-47c2-8c37-41eebfc4fe3f'
        self.node_addon.save()

        responses.add(
            responses.GET,
            urlparse.urljoin(API_URL, 'folders'),
            body=mock_responses['folders'],
            content_type='application/json'
        )

        responses.add(
            responses.GET,
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

    '''
    TODO
    def test_citation_list_bibtex(self):
        #"""JSON: list of formatted citations in BibTeX style"""
        assert_true(False)
    '''
