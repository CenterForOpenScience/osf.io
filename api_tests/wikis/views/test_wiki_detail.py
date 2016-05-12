import furl
from urlparse import urlparse
from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE
from tests.base import ApiWikiTestCase
from tests.factories import (ProjectFactory, RegistrationFactory,
                             NodeWikiFactory, PrivateLinkFactory)


class WikiDetailMixin(object):
    def _set_up_public_project_with_wiki_page(self):
        raise NotImplementedError

    def _set_up_private_project_with_wiki_page(self):
        raise NotImplementedError

    def _set_up_public_registration_with_wiki_page(self):
        raise NotImplementedError

    def _set_up_private_registration_with_wiki_page(self):
        raise NotImplementedError

    def test_public_node_logged_out_user_can_view_wiki(self):
        self._set_up_public_project_with_wiki_page()
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.public_wiki._id)

    def test_public_node_logged_in_non_contributor_can_view_wiki(self):
        self._set_up_public_project_with_wiki_page()
        res = self.app.get(self.public_url, auth=self.non_contributor.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.public_wiki._id)

    def test_public_node_logged_in_contributor_can_view_wiki(self):
        self._set_up_public_project_with_wiki_page()
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.public_wiki._id)

    def test_private_node_logged_out_user_cannot_view_wiki(self):
        self._set_up_private_project_with_wiki_page()
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

    def test_private_node_logged_in_non_contributor_cannot_view_wiki(self):
        self._set_up_private_project_with_wiki_page()
        res = self.app.get(self.private_url, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_private_node_logged_in_contributor_can_view_wiki(self):
        self._set_up_private_project_with_wiki_page()
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.private_wiki._id)

    def test_private_node_user_with_anonymous_link_can_view_wiki(self):
        self._set_up_private_project_with_wiki_page()
        private_link = PrivateLinkFactory(anonymous=True)
        private_link.nodes.append(self.private_project)
        private_link.save()
        url = furl.furl(self.private_url).add(query_params={'view_only': private_link.key}).url
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.private_wiki._id)

    def test_private_node_user_with_view_only_link_can_view_wiki(self):
        self._set_up_private_project_with_wiki_page()
        private_link = PrivateLinkFactory(anonymous=False)
        private_link.nodes.append(self.private_project)
        private_link.save()
        url = furl.furl(self.private_url).add(query_params={'view_only': private_link.key}).url
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.private_wiki._id)

    def test_public_registration_logged_out_user_cannot_view_wiki(self):
        self._set_up_public_registration_with_wiki_page()
        res = self.app.get(self.public_registration_url, expect_errors=True)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.public_registration_wiki_id)

    def test_public_registration_logged_in_non_contributor_cannot_view_wiki(self):
        self._set_up_public_registration_with_wiki_page()
        res = self.app.get(self.public_registration_url, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.public_registration_wiki_id)

    def test_public_registration_contributor_can_view_wiki(self):
        self._set_up_public_registration_with_wiki_page()
        res = self.app.get(self.public_registration_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.public_registration_wiki_id)

    def test_private_registration_logged_out_user_cannot_view_wiki(self):
        self._set_up_private_registration_with_wiki_page()
        res = self.app.get(self.private_registration_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

    def test_private_registration_logged_in_non_contributor_cannot_view_wiki(self):
        self._set_up_private_registration_with_wiki_page()
        res = self.app.get(self.private_registration_url, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_private_registration_contributor_can_view_wiki(self):
        self._set_up_private_registration_with_wiki_page()
        res = self.app.get(self.private_registration_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.private_registration_wiki_id)

    def test_wiki_has_user_link(self):
        self._set_up_public_project_with_wiki_page()
        res = self.app.get(self.public_url)
        url = res.json['data']['relationships']['user']['links']['related']['href']
        expected_url = '/{}users/{}/'.format(API_BASE, self.user._id)
        assert_equal(res.status_code, 200)
        assert_equal(urlparse(url).path, expected_url)

    def test_wiki_has_node_link(self):
        self._set_up_public_project_with_wiki_page()
        res = self.app.get(self.public_url)
        url = res.json['data']['relationships']['node']['links']['related']['href']
        expected_url = '/{}nodes/{}/'.format(API_BASE, self.public_project._id)
        assert_equal(res.status_code, 200)
        assert_equal(urlparse(url).path, expected_url)

    def test_wiki_has_comments_link(self):
        self._set_up_public_project_with_wiki_page()
        res = self.app.get(self.public_url)
        url = res.json['data']['relationships']['comments']['links']['related']['href']
        expected_url = '/{}nodes/{}/comments/?filter[target]={}'.format(API_BASE, self.public_project._id, self.public_wiki._id)
        assert_equal(res.status_code, 200)
        assert_in(expected_url, url)

    def test_wiki_has_download_link(self):
        self._set_up_public_project_with_wiki_page()
        res = self.app.get(self.public_url)
        url = res.json['data']['links']['download']
        expected_url = '/{}wikis/{}/content/'.format(API_BASE, self.public_wiki._id)
        assert_equal(res.status_code, 200)
        assert_in(expected_url, url)


class TestWikiDetailView(ApiWikiTestCase, WikiDetailMixin):

    def _set_up_public_project_with_wiki_page(self):
        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_wiki = self._add_project_wiki_page(self.public_project, self.user)
        self.public_url = '/{}wikis/{}/'.format(API_BASE, self.public_wiki._id)

    def _set_up_private_project_with_wiki_page(self):
        self.private_project = ProjectFactory(creator=self.user)
        self.private_wiki = self._add_project_wiki_page(self.private_project, self.user)
        self.private_url = '/{}wikis/{}/'.format(API_BASE, self.private_wiki._id)

    def _set_up_public_registration_with_wiki_page(self):
        self._set_up_public_project_with_wiki_page()
        self.public_registration = RegistrationFactory(project=self.public_project, user=self.user, is_public=True)
        self.public_registration_wiki_id = self.public_registration.wiki_pages_versions['home'][0]
        self.public_registration.wiki_pages_current = {'home': self.public_registration_wiki_id}
        self.public_registration.save()
        self.public_registration_url = '/{}wikis/{}/'.format(API_BASE, self.public_registration_wiki_id)

    def _set_up_private_registration_with_wiki_page(self):
        self._set_up_private_project_with_wiki_page()
        self.private_registration = RegistrationFactory(project=self.private_project, user=self.user)
        self.private_registration_wiki_id = self.private_registration.wiki_pages_versions['home'][0]
        self.private_registration.wiki_pages_current = {'home': self.private_registration_wiki_id}
        self.private_registration.save()
        self.private_registration_url = '/{}wikis/{}/'.format(API_BASE, self.private_registration_wiki_id)

    def test_wiki_invalid_id_not_found(self):
        url = '/{}wikis/{}/'.format(API_BASE, 'abcde')
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_old_wiki_versions_not_returned(self):
        self._set_up_public_project_with_wiki_page()
        current_wiki = NodeWikiFactory(project=self.public_project, user=self.user)
        url = '/{}wikis/{}/'.format(API_BASE, current_wiki._id)
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 404)
