# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE

from tests.base import ApiWikiTestCase, ApiTestCase
from tests.factories import AuthUserFactory, ProjectFactory, NodeWikiFactory, RegistrationFactory


class TestNodeWikiList(ApiWikiTestCase):

    def _set_up_public_project_with_wiki_page(self):
        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_wiki = self._add_project_wiki_page(self.public_project, self.user)
        self.public_url = '/{}nodes/{}/wikis/'.format(API_BASE, self.public_project._id)

    def _set_up_private_project_with_wiki_page(self):
        self.private_project = ProjectFactory(creator=self.user)
        self.private_wiki = self._add_project_wiki_page(self.private_project, self.user)
        self.private_url = '/{}nodes/{}/wikis/'.format(API_BASE, self.private_project._id)

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


class TestFilterNodeWikiList(ApiTestCase):

    def setUp(self):
        super(TestFilterNodeWikiList, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.base_url = '/{}nodes/{}/wikis/'.format(API_BASE, self.project._id)
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
