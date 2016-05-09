from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE
from tests.base import ApiTestCase
from tests.factories import (AuthUserFactory, ProjectFactory, RegistrationFactory,
                             NodeWikiFactory, PrivateLinkFactory)


class TestNodeWikiDetailView(ApiTestCase):
    def setUp(self):
        super(TestNodeWikiDetailView, self).setUp()
        self.user = AuthUserFactory()
        self.non_contributor = AuthUserFactory()

    def _add_project_wiki_page(self, node, user):
        # API will only return current wiki pages
        return NodeWikiFactory(node=node, user=user, is_current=True)

    def _set_up_public_project_with_wiki_page(self):
        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_wiki = self._add_project_wiki_page(self.public_project, self.user)
        self.public_url = '/{}nodes/{}/wikis/{}/'.format(API_BASE, self.public_project._id, self.public_wiki._id)

    def _set_up_private_project_with_wiki_page(self):
        self.private_project = ProjectFactory(creator=self.user)
        self.private_wiki = self._add_project_wiki_page(self.private_project, self.user)
        self.private_url = '/{}nodes/{}/wikis/{}/'.format(API_BASE, self.private_project._id, self.private_wiki._id)

    def _set_up_public_registration_with_wiki_page(self):
        self._set_up_public_project_with_wiki_page()
        self.public_registration = RegistrationFactory(project=self.public_project, user=self.user, is_public=True)
        self.public_registration_wiki_id = self.public_registration.wiki_pages_versions['home'][0]
        self.public_registration.wiki_pages_current = {'home': self.public_registration_wiki_id}
        self.public_registration.save()
        self.public_registration_url = '/{}nodes/{}/wikis/{}/'.format(API_BASE, self.public_registration._id, self.public_registration_wiki_id)

    def _set_up_private_registration_with_wiki_page(self):
        self._set_up_private_project_with_wiki_page()
        self.private_registration = RegistrationFactory(project=self.private_project, user=self.user)
        self.private_registration_wiki_id = self.private_registration.wiki_pages_versions['home'][0]
        self.private_registration.wiki_pages_current = {'home': self.private_registration_wiki_id}
        self.private_registration.save()
        self.private_registration_url = '/{}nodes/{}/wikis/{}/'.format(API_BASE, self.private_registration._id, self.private_registration_wiki_id)

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
        res = self.app.get('/{}nodes/{}/wikis/{}/'.format(API_BASE, self.private_project._id, self.private_wiki._id),
                           {'view_only': private_link.key})
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.private_wiki._id)

    def test_private_node_user_with_view_only_link_can_view_wiki(self):
        self._set_up_private_project_with_wiki_page()
        private_link = PrivateLinkFactory(anonymous=False)
        private_link.nodes.append(self.private_project)
        private_link.save()
        res = self.app.get('/{}nodes/{}/wikis/{}/'.format(API_BASE, self.private_project._id, self.private_wiki._id),
                           {'view_only': private_link.key})
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

    def test_wiki_invalid_id_not_found(self):
        url = '/{}nodes/{}wikis/{}/'.format(API_BASE, ProjectFactory()._id, 'abcde')
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_old_wiki_versions_not_returned(self):
        self._set_up_public_project_with_wiki_page()
        current_wiki = NodeWikiFactory(project=self.public_project, user=self.user)
        url = '/nodes{}/{}wikis/{}/'.format(API_BASE, self.public_project._id, current_wiki._id)
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 404)