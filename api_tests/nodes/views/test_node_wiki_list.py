# -*- coding: utf-8 -*-
import mock
from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE

from tests.base import ApiWikiTestCase, ApiTestCase
from osf_tests.factories import AuthUserFactory, ProjectFactory, RegistrationFactory
from addons.wiki.tests.factories import NodeWikiFactory


class TestNodeWikiList(ApiWikiTestCase):

    def _set_up_public_project_with_wiki_page(self):
        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_wiki = self._add_project_wiki_page(self.public_project, self.user)
        self.public_url = '/{}nodes/{}/wikis/'.format(API_BASE, self.public_project._id)

    def _set_up_private_project_with_wiki_page(self):
        self.private_project = ProjectFactory(creator=self.user)
        self.private_wiki = self._add_project_wiki_page(self.private_project, self.user)
        self.private_url = '/{}nodes/{}/wikis/'.format(API_BASE, self.private_project._id)

    def _set_up_public_registration_with_wiki_page(self):
        self._set_up_public_project_with_wiki_page()
        self.public_registration = RegistrationFactory(project=self.public_project, user=self.user, is_public=True)
        self.public_registration_wiki_id = self.public_registration.wiki_pages_versions['home'][0]
        self.public_registration.wiki_pages_current = {'home': self.public_registration_wiki_id}
        self.public_registration.save()
        self.public_registration_url = '/{}registrations/{}/wikis/'.format(API_BASE, self.public_registration._id)

    def _set_up_registration_with_wiki_page(self):
        self._set_up_private_project_with_wiki_page()
        self.registration = RegistrationFactory(project=self.private_project, user=self.user)
        self.registration_wiki_id = self.registration.wiki_pages_versions['home'][0]
        self.registration.wiki_pages_current = {'home': self.registration_wiki_id}
        self.registration.save()
        self.registration_url = '/{}registrations/{}/wikis/'.format(API_BASE, self.registration._id)

    def test_return_public_node_wikis_logged_out_user(self):
        self._set_up_public_project_with_wiki_page()
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        wiki_ids = [wiki['id'] for wiki in res.json['data']]
        assert_in(self.public_wiki._id, wiki_ids)

    def test_return_public_node_wikis_logged_in_non_contributor(self):
        self._set_up_public_project_with_wiki_page()
        res = self.app.get(self.public_url, auth=self.non_contributor.auth)
        assert_equal(res.status_code, 200)
        wiki_ids = [wiki['id'] for wiki in res.json['data']]
        assert_in(self.public_wiki._id, wiki_ids)

    def test_return_public_node_wikis_logged_in_contributor(self):
        self._set_up_public_project_with_wiki_page()
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        wiki_ids = [wiki['id'] for wiki in res.json['data']]
        assert_in(self.public_wiki._id, wiki_ids)

    def test_return_private_node_wikis_logged_out_user(self):
        self._set_up_private_project_with_wiki_page()
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

    def test_return_private_node_wikis_logged_in_non_contributor(self):
        self._set_up_private_project_with_wiki_page()
        res = self.app.get(self.private_url, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_return_private_node_wikis_logged_in_contributor(self):
        self._set_up_private_project_with_wiki_page()
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        wiki_ids = [wiki['id'] for wiki in res.json['data']]
        assert_in(self.private_wiki._id, wiki_ids)

    def test_return_registration_wikis_logged_out_user(self):
        self._set_up_registration_with_wiki_page()
        res = self.app.get(self.registration_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

    def test_return_registration_wikis_logged_in_non_contributor(self):
        self._set_up_registration_with_wiki_page()
        res = self.app.get(self.registration_url, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_return_registration_wikis_logged_in_contributor(self):
        self._set_up_registration_with_wiki_page()
        res = self.app.get(self.registration_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        wiki_ids = [wiki['id'] for wiki in res.json['data']]
        assert_in(self.registration_wiki_id, wiki_ids)

    def test_wikis_not_returned_for_withdrawn_registration(self):
        self._set_up_registration_with_wiki_page()
        self.registration.is_public = True
        withdrawal = self.registration.retract_registration(user=self.user, save=True)
        token = withdrawal.approval_state.values()[0]['approval_token']
        # TODO: Remove mocking when StoredFileNode is implemented
        with mock.patch('osf.models.AbstractNode.update_search'):
            withdrawal.approve_retraction(self.user, token)
            withdrawal.save()
        res = self.app.get(self.registration_url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_public_node_wikis_relationship_links(self):
        self._set_up_public_project_with_wiki_page()
        res = self.app.get(self.public_url)
        expected_nodes_relationship_url = '{}nodes/{}/'.format(API_BASE, self.public_project._id)
        expected_comments_relationship_url = '{}nodes/{}/comments/'.format(API_BASE, self.public_project._id)
        assert_in(expected_nodes_relationship_url, res.json['data'][0]['relationships']['node']['links']['related']['href'])
        assert_in(expected_comments_relationship_url, res.json['data'][0]['relationships']['comments']['links']['related']['href'])

    def test_private_node_wikis_relationship_links(self):
        self._set_up_private_project_with_wiki_page()
        res = self.app.get(self.private_url, auth=self.user.auth)
        expected_nodes_relationship_url = '{}nodes/{}/'.format(API_BASE, self.private_project._id)
        expected_comments_relationship_url = '{}nodes/{}/comments/'.format(API_BASE, self.private_project._id)
        assert_in(expected_nodes_relationship_url, res.json['data'][0]['relationships']['node']['links']['related']['href'])
        assert_in(expected_comments_relationship_url, res.json['data'][0]['relationships']['comments']['links']['related']['href'])

    def test_public_registration_wikis_relationship_links(self):
        self._set_up_public_registration_with_wiki_page()
        res = self.app.get(self.public_registration_url)
        expected_nodes_relationship_url = '{}registrations/{}/'.format(API_BASE, self.public_registration._id)
        expected_comments_relationship_url = '{}registrations/{}/comments/'.format(API_BASE, self.public_registration._id)
        assert_in(expected_nodes_relationship_url, res.json['data'][0]['relationships']['node']['links']['related']['href'])
        assert_in(expected_comments_relationship_url, res.json['data'][0]['relationships']['comments']['links']['related']['href'])

    def test_private_registration_wikis_relationship_links(self):
        self._set_up_registration_with_wiki_page()
        res = self.app.get(self.registration_url, auth=self.user.auth)
        expected_nodes_relationship_url = '{}registrations/{}/'.format(API_BASE, self.registration._id)
        expected_comments_relationship_url = '{}registrations/{}/comments/'.format(API_BASE, self.registration._id)
        assert_in(expected_nodes_relationship_url, res.json['data'][0]['relationships']['node']['links']['related']['href'])
        assert_in(expected_comments_relationship_url, res.json['data'][0]['relationships']['comments']['links']['related']['href'])

    def test_registration_wikis_not_returned_from_nodes_endpoint(self):
        self._set_up_public_project_with_wiki_page()
        self._set_up_public_registration_with_wiki_page()
        res = self.app.get(self.public_url)
        node_relationships = [
            node_wiki['relationships']['node']['links']['related']['href']
            for node_wiki in res.json['data']
        ]
        assert_equal(res.status_code, 200)
        assert_equal(len(node_relationships), 1)
        assert_in(self.public_project._id, node_relationships[0])

    def test_node_wikis_not_returned_from_registrations_endpoint(self):
        self._set_up_public_project_with_wiki_page()
        self._set_up_public_registration_with_wiki_page()
        res = self.app.get(self.public_registration_url)
        node_relationships = [
            node_wiki['relationships']['node']['links']['related']['href']
            for node_wiki in res.json['data']
            ]
        assert_equal(res.status_code, 200)
        assert_equal(len(node_relationships), 1)
        assert_in(self.public_registration._id, node_relationships[0])


class TestFilterNodeWikiList(ApiTestCase):

    def setUp(self):
        super(TestFilterNodeWikiList, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.base_url = '/{}nodes/{}/wikis/'.format(API_BASE, self.project._id)
        # TODO: Remove mocking when StoredFileNode is implemented
        with mock.patch('osf.models.AbstractNode.update_search'):
            self.wiki = NodeWikiFactory(node=self.project, user=self.user)
        self.date = self.wiki.date.strftime('%Y-%m-%dT%H:%M:%S.%f')

    def test_node_wikis_with_no_filter_returns_all(self):
        res = self.app.get(self.base_url, auth=self.user.auth)
        wiki_ids = [wiki['id'] for wiki in res.json['data']]
        assert_in(self.wiki._id, wiki_ids)

    def test_filter_wikis_by_page_name(self):
        url = self.base_url + '?filter[name]=home'
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['attributes']['name'], 'home')

    def test_filter_wikis_modified_on_date(self):
        url = self.base_url + '?filter[date_modified][eq]={}'.format(self.date)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)

    def test_filter_wikis_modified_before_date(self):
        url = self.base_url + '?filter[date_modified][lt]={}'.format(self.date)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 0)

    def test_filter_wikis_modified_after_date(self):
        url = self.base_url + '?filter[date_modified][gt]={}'.format(self.date)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 0)
