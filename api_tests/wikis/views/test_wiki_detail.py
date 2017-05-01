import mock
import pytest
import furl
from urlparse import urlparse
from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE

from framework.guid.model import Guid

from addons.wiki.models import NodeWikiPage

from tests.base import ApiWikiTestCase
from osf_tests.factories import (ProjectFactory, RegistrationFactory,
                                 PrivateLinkFactory, CommentFactory)
from addons.wiki.tests.factories import NodeWikiFactory


class TestWikiDetailView(ApiWikiTestCase):

    def _set_up_public_project_with_wiki_page(self, project_options=None):
        project_options = project_options or {}
        self.public_project = ProjectFactory(is_public=True, creator=self.user, **project_options)
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
        private_link.nodes.add(self.private_project)
        private_link.save()
        url = furl.furl(self.private_url).add(query_params={'view_only': private_link.key}).url
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.private_wiki._id)

    def test_private_node_user_with_view_only_link_can_view_wiki(self):
        self._set_up_private_project_with_wiki_page()
        private_link = PrivateLinkFactory(anonymous=False)
        private_link.nodes.add(self.private_project)
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

    def test_user_cannot_view_withdrawn_registration_wikis(self):
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
        assert_equal(res.status_code, 200)
        url = res.json['data']['relationships']['comments']['links']['related']['href']
        comment = CommentFactory(node=self.public_project, target=Guid.load(self.public_wiki._id), user=self.user)
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['type'], 'comments')

    def test_only_project_contrib_can_comment_on_closed_project(self):
        self._set_up_public_project_with_wiki_page(project_options={'comment_level': 'private'})
        res = self.app.get(self.public_url, auth=self.user.auth)
        can_comment = res.json['data']['attributes']['current_user_can_comment']
        assert_equal(res.status_code, 200)
        assert_equal(can_comment, True)

        res = self.app.get(self.public_url, auth=self.non_contributor.auth)
        can_comment = res.json['data']['attributes']['current_user_can_comment']
        assert_equal(res.status_code, 200)
        assert_equal(can_comment, False)

    def test_any_loggedin_user_can_comment_on_open_project(self):
        self._set_up_public_project_with_wiki_page(project_options={'comment_level': 'public'})
        res = self.app.get(self.public_url, auth=self.non_contributor.auth)
        can_comment = res.json['data']['attributes']['current_user_can_comment']
        assert_equal(res.status_code, 200)
        assert_equal(can_comment, True)

    def test_non_logged_in_user_cant_comment(self):
        self._set_up_public_project_with_wiki_page(project_options={'comment_level': 'public'})
        res = self.app.get(self.public_url)
        can_comment = res.json['data']['attributes']['current_user_can_comment']
        assert_equal(res.status_code, 200)
        assert_equal(can_comment, False)

    def test_wiki_has_download_link(self):
        self._set_up_public_project_with_wiki_page()
        res = self.app.get(self.public_url)
        url = res.json['data']['links']['download']
        expected_url = '/{}wikis/{}/content/'.format(API_BASE, self.public_wiki._id)
        assert_equal(res.status_code, 200)
        assert_in(expected_url, url)

    def test_wiki_invalid_id_not_found(self):
        url = '/{}wikis/{}/'.format(API_BASE, 'abcde')
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_old_wiki_versions_not_returned(self):
        self._set_up_public_project_with_wiki_page()
        # TODO: Remove mocking when StoredFileNode is implemented
        with mock.patch('osf.models.AbstractNode.update_search'):
            current_wiki = NodeWikiFactory(node=self.public_project, user=self.user)
        old_version_id = self.public_project.wiki_pages_versions[current_wiki.page_name][-2]
        old_version = NodeWikiPage.load(old_version_id)
        url = '/{}wikis/{}/'.format(API_BASE, old_version._id)
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_public_node_wiki_relationship_links(self):
        self._set_up_public_project_with_wiki_page()
        res = self.app.get(self.public_url)
        expected_nodes_relationship_url = '{}nodes/{}/'.format(API_BASE, self.public_project._id)
        expected_comments_relationship_url = '{}nodes/{}/comments/'.format(API_BASE, self.public_project._id)
        assert_in(expected_nodes_relationship_url, res.json['data']['relationships']['node']['links']['related']['href'])
        assert_in(expected_comments_relationship_url, res.json['data']['relationships']['comments']['links']['related']['href'])

    def test_private_node_wiki_relationship_links(self):
        self._set_up_private_project_with_wiki_page()
        res = self.app.get(self.private_url, auth=self.user.auth)
        expected_nodes_relationship_url = '{}nodes/{}/'.format(API_BASE, self.private_project._id)
        expected_comments_relationship_url = '{}nodes/{}/comments/'.format(API_BASE, self.private_project._id)
        assert_in(expected_nodes_relationship_url, res.json['data']['relationships']['node']['links']['related']['href'])
        assert_in(expected_comments_relationship_url, res.json['data']['relationships']['comments']['links']['related']['href'])

    def test_public_registration_wiki_relationship_links(self):
        self._set_up_public_registration_with_wiki_page()
        res = self.app.get(self.public_registration_url)
        expected_nodes_relationship_url = '{}registrations/{}/'.format(API_BASE, self.public_registration._id)
        expected_comments_relationship_url = '{}registrations/{}/comments/'.format(API_BASE, self.public_registration._id)
        assert_in(expected_nodes_relationship_url, res.json['data']['relationships']['node']['links']['related']['href'])
        assert_in(expected_comments_relationship_url, res.json['data']['relationships']['comments']['links']['related']['href'])

    def test_private_registration_wiki_relationship_links(self):
        self._set_up_private_registration_with_wiki_page()
        res = self.app.get(self.private_registration_url, auth=self.user.auth)
        expected_nodes_relationship_url = '{}registrations/{}/'.format(API_BASE, self.private_registration._id)
        expected_comments_relationship_url = '{}registrations/{}/comments/'.format(API_BASE, self.private_registration._id)
        assert_in(expected_nodes_relationship_url, res.json['data']['relationships']['node']['links']['related']['href'])
        assert_in(expected_comments_relationship_url, res.json['data']['relationships']['comments']['links']['related']['href'])
