import mock
import furl
import datetime
import pytz
from future.moves.urllib.parse import urlparse
from nose.tools import *  # noqa:

from api.base.settings.defaults import API_BASE

from addons.wiki.models import WikiVersion, WikiPage

from tests.base import ApiWikiTestCase
from osf_tests.factories import (ProjectFactory, RegistrationFactory,
                                 PrivateLinkFactory)


class TestWikiVersionDetailView(ApiWikiTestCase):

    def _set_up_public_project_with_wiki_page(self, project_options=None):
        project_options = project_options or {}
        self.public_project = ProjectFactory(is_public=True, creator=self.user, **project_options)
        from addons.wiki.tests.factories import WikiFactory, WikiVersionFactory
        with mock.patch('osf.models.AbstractNode.update_search'):
            self.public_wiki_page = WikiFactory(node=self.public_project, user=self.user)
            self.public_wiki_version = WikiVersionFactory(wiki_page=self.public_wiki_page, user=self.user)
        self.public_url = '/{}wikis/{}/versions/{}/'.format(API_BASE, self.public_wiki_page._id, str(self.public_wiki_version.identifier))
        return self.public_wiki_version

    def _set_up_private_project_with_wiki_page(self):
        self.private_project = ProjectFactory(creator=self.user)
        self.private_wiki_version = self._add_project_wiki_version(self.private_project, self.user)
        self.private_url = '/{}wikis/{}/versions/{}/'.format(API_BASE, self.private_wiki_version.wiki_page._id, str(self.private_wiki_version.identifier))

    def _set_up_public_registration_with_wiki_page(self):
        self._set_up_public_project_with_wiki_page()
        self.public_registration = RegistrationFactory(project=self.public_project, user=self.user, is_public=True)
        self.public_registration_wiki_version = WikiVersion.objects.get_for_node(self.public_registration, 'home')
        self.public_registration.save()
        self.public_registration_url = '/{}wikis/{}/versions/{}/'.format(API_BASE, self.public_registration_wiki_version.wiki_page._id, str(self.public_registration_wiki_version.identifier))

    def _set_up_private_registration_with_wiki_page(self):
        self._set_up_private_project_with_wiki_page()
        self.private_registration = RegistrationFactory(project=self.private_project, user=self.user)
        self.private_registration_wiki_version = WikiVersion.objects.get_for_node(self.private_registration, 'home')
        self.private_registration.save()
        self.private_registration_url = '/{}wikis/{}/versions/{}/'.format(API_BASE, self.private_registration_wiki_version.wiki_page._id, str(self.private_registration_wiki_version.identifier))

    def test_public_node_logged_out_user_can_view_wiki_version(self):
        self._set_up_public_project_with_wiki_page()
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], str(self.public_wiki_version.identifier))

    def test_public_node_logged_in_non_contributor_can_view_wiki_version(self):
        self._set_up_public_project_with_wiki_page()
        res = self.app.get(self.public_url, auth=self.non_contributor.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], str(self.public_wiki_version.identifier))

    def test_public_node_logged_in_contributor_can_view_wiki_version(self):
        self._set_up_public_project_with_wiki_page()
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], str(self.public_wiki_version.identifier))

    def test_private_node_logged_out_user_cannot_view_wiki_version(self):
        self._set_up_private_project_with_wiki_page()
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

    def test_private_node_logged_in_non_contributor_cannot_view_wiki_version(self):
        self._set_up_private_project_with_wiki_page()
        res = self.app.get(self.private_url, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_private_node_logged_in_contributor_can_view_wiki_version(self):
        self._set_up_private_project_with_wiki_page()
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], str(self.private_wiki_version.identifier))

    def test_private_node_user_with_anonymous_link_can_view_wiki_version(self):
        self._set_up_private_project_with_wiki_page()
        private_link = PrivateLinkFactory(anonymous=True)
        private_link.nodes.add(self.private_project)
        private_link.save()
        url = furl.furl(self.private_url).add(query_params={'view_only': private_link.key}).url
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], str(self.private_wiki_version.identifier))

    def test_private_node_user_with_view_only_link_can_view_wiki_version(self):
        self._set_up_private_project_with_wiki_page()
        private_link = PrivateLinkFactory(anonymous=False)
        private_link.nodes.add(self.private_project)
        private_link.save()
        url = furl.furl(self.private_url).add(query_params={'view_only': private_link.key}).url
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], str(self.private_wiki_version.identifier))

    def test_public_registration_logged_out_user_cannot_view_wiki_version(self):
        self._set_up_public_registration_with_wiki_page()
        res = self.app.get(self.public_registration_url, expect_errors=True)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], str(self.public_registration_wiki_version.identifier))

    def test_public_registration_logged_in_non_contributor_cannot_view_wiki_version(self):
        self._set_up_public_registration_with_wiki_page()
        res = self.app.get(self.public_registration_url, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], str(self.public_registration_wiki_version.identifier))

    def test_public_registration_contributor_can_view_wiki_version(self):
        self._set_up_public_registration_with_wiki_page()
        res = self.app.get(self.public_registration_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], str(self.public_registration_wiki_version.identifier))

    def test_user_cannot_view_withdrawn_registration_wiki_versions(self):
        self._set_up_public_registration_with_wiki_page()
        # TODO: Remove mocking when StoredFileNode is implemented
        with mock.patch('osf.models.AbstractNode.update_search'):
            withdrawal = self.public_registration.retract_registration(user=self.user, save=True)
            token = withdrawal.approval_state.values()[0]['approval_token']
            withdrawal.approve_retraction(self.user, token)
            withdrawal.save()
        res = self.app.get(self.public_registration_url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_private_registration_logged_out_user_cannot_view_wiki_version(self):
        self._set_up_private_registration_with_wiki_page()
        res = self.app.get(self.private_registration_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

    def test_private_registration_logged_in_non_contributor_cannot_view_wiki_version(self):
        self._set_up_private_registration_with_wiki_page()
        res = self.app.get(self.private_registration_url, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_private_registration_contributor_can_view_wiki_version(self):
        self._set_up_private_registration_with_wiki_page()
        res = self.app.get(self.private_registration_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], str(self.private_registration_wiki_version.identifier))

    def test_wiki_version_has_user_link(self):
        self._set_up_public_project_with_wiki_page()
        res = self.app.get(self.public_url)
        url = res.json['data']['relationships']['user']['links']['related']['href']
        expected_url = '/{}users/{}/'.format(API_BASE, self.user._id)
        assert_equal(res.status_code, 200)
        assert_equal(urlparse(url).path, expected_url)

    def test_wiki_version_has_wiki_page_link(self):
        self._set_up_public_project_with_wiki_page()
        res = self.app.get(self.public_url)
        url = res.json['data']['relationships']['wiki_page']['links']['related']['href']
        expected_url = '/{}wikis/{}/'.format(API_BASE, self.public_wiki_version.wiki_page._id)
        assert_equal(res.status_code, 200)
        assert_equal(urlparse(url).path, expected_url)

    def test_wiki_version_has_download_link(self):
        self._set_up_public_project_with_wiki_page()
        res = self.app.get(self.public_url)
        url = res.json['data']['links']['download']
        expected_url = '/{}wikis/{}/versions/{}/content'.format(API_BASE, self.public_wiki_version.wiki_page._id, str(self.public_wiki_version.identifier))
        assert_equal(res.status_code, 200)
        assert_in(expected_url, url)

    def test_wiki_version_invalid_identifier_not_found(self):
        self._set_up_public_project_with_wiki_page()
        url = '/{}wikis/{}/versions/{}/'.format(API_BASE, self.public_wiki_page._id, 500)
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_deleted_wiki_version_not_returned(self):
        self._set_up_public_project_with_wiki_page()
        url = '/{}wikis/{}/versions/{}/'.format(API_BASE, self.public_wiki_page._id, str(self.public_wiki_version.identifier))
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        self.public_wiki_version.wiki_page.deleted = datetime.datetime(2017, 3, 16, 11, 00, tzinfo=pytz.utc)
        self.public_wiki_version.wiki_page.save()

        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 410)

    def test_public_node_wiki_version_relationship_links(self):
        self._set_up_public_project_with_wiki_page()
        res = self.app.get(self.public_url)
        expected_wiki_page_relationship_url = '{}wikis/{}/'.format(API_BASE, self.public_wiki_version.wiki_page._id)
        expected_user_relationship_url = '{}users/{}/'.format(API_BASE, self.user._id)
        assert_in(expected_wiki_page_relationship_url, res.json['data']['relationships']['wiki_page']['links']['related']['href'])
        assert_in(expected_user_relationship_url, res.json['data']['relationships']['user']['links']['related']['href'])

    def test_private_node_wiki_version_relationship_links(self):
        self._set_up_private_project_with_wiki_page()
        res = self.app.get(self.private_url, auth=self.user.auth)
        expected_wiki_page_relationship_url = '{}wikis/{}/'.format(API_BASE, self.private_wiki_version.wiki_page._id)
        expected_user_relationship_url = '{}users/{}/'.format(API_BASE, self.user._id)
        assert_in(expected_wiki_page_relationship_url, res.json['data']['relationships']['wiki_page']['links']['related']['href'])
        assert_in(expected_user_relationship_url, res.json['data']['relationships']['user']['links']['related']['href'])

    def test_public_registration_wiki_version_relationship_links(self):
        self._set_up_public_registration_with_wiki_page()
        res = self.app.get(self.public_registration_url)
        expected_wiki_page_url = '{}wikis/{}/'.format(API_BASE, WikiPage.objects.get_for_node(self.public_registration, 'home')._id)
        expected_user_relationship_url = '{}users/{}/'.format(API_BASE, self.user._id)
        assert_in(expected_wiki_page_url, res.json['data']['relationships']['wiki_page']['links']['related']['href'])
        assert_in(expected_user_relationship_url, res.json['data']['relationships']['user']['links']['related']['href'])

    def test_private_registration_wiki_version_relationship_links(self):
        self._set_up_private_registration_with_wiki_page()
        res = self.app.get(self.private_registration_url, auth=self.user.auth)
        expected_wiki_page_url = '{}wikis/{}/'.format(API_BASE, WikiPage.objects.get_for_node(self.private_registration, 'home')._id)
        expected_user_relationship_url = '{}users/{}/'.format(API_BASE, self.user._id)
        assert_in(expected_wiki_page_url, res.json['data']['relationships']['wiki_page']['links']['related']['href'])
        assert_in(expected_user_relationship_url, res.json['data']['relationships']['user']['links']['related']['href'])
