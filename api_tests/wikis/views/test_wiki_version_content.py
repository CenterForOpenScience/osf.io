from nose.tools import *  # noqa:

from addons.wiki.models import WikiVersion
from api.base.settings.defaults import API_BASE

from tests.base import ApiWikiTestCase
from osf_tests.factories import ProjectFactory, RegistrationFactory


class TestWikiVersionContentView(ApiWikiTestCase):

    def _set_up_public_project_with_wiki_page(self):
        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_wiki = self._add_project_wiki_version(self.public_project, self.user)
        self.public_url = '/{}wikis/{}/versions/{}/content/'.format(API_BASE, self.public_wiki.wiki_page._id, self.public_wiki.identifier)

    def _set_up_private_project_with_wiki_page(self):
        self.private_project = ProjectFactory(creator=self.user)
        self.private_wiki = self._add_project_wiki_version(self.private_project, self.user)
        self.private_url = '/{}wikis/{}/versions/{}/content/'.format(API_BASE, self.private_wiki.wiki_page._id, self.private_wiki.identifier)

    def _set_up_public_registration_with_wiki_page(self):
        self._set_up_public_project_with_wiki_page()
        self.public_registration = RegistrationFactory(project=self.public_project, user=self.user, is_public=True)
        self.public_registration_wiki = WikiVersion.objects.get_for_node(self.public_registration, 'home')
        self.public_registration.save()
        self.public_registration_url = '/{}wikis/{}/versions/{}/content/'.format(API_BASE, self.public_registration_wiki.wiki_page._id, self.public_registration_wiki.identifier)

    def test_logged_out_user_can_get_public_wiki_content(self):
        self._set_up_public_project_with_wiki_page()
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'text/markdown')
        assert_equal(res.body.decode(), self.public_wiki.content)

    def test_logged_in_non_contributor_can_get_public_wiki_content(self):
        self._set_up_public_project_with_wiki_page()
        res = self.app.get(self.public_url, auth=self.non_contributor.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'text/markdown')
        assert_equal(res.body.decode(), self.public_wiki.content)

    def test_logged_in_contributor_can_get_public_wiki_content(self):
        self._set_up_public_project_with_wiki_page()
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'text/markdown')
        assert_equal(res.body.decode(), self.public_wiki.content)

    def test_logged_out_user_cannot_get_private_wiki_content(self):
        self._set_up_private_project_with_wiki_page()
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_logged_in_non_contributor_cannot_get_private_wiki_content(self):
        self._set_up_private_project_with_wiki_page()
        res = self.app.get(self.private_url, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_logged_in_contributor_can_get_private_wiki_content(self):
        self._set_up_private_project_with_wiki_page()
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'text/markdown')
        assert_equal(res.body.decode(), self.private_wiki.content)

    def test_older_versions_content_can_be_accessed(self):
        self._set_up_private_project_with_wiki_page()
        # Create a second version
        wiki_version = self.private_wiki.wiki_page.update(self.user, 'Second draft of wiki')
        wiki_page = wiki_version.wiki_page
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'text/markdown')
        assert_equal(res.body.decode(), self.private_wiki.content)

        self.private_url_latest = '/{}wikis/{}/versions/{}/content/'.format(API_BASE, wiki_page._id, wiki_version.identifier)
        res = self.app.get(self.private_url_latest, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'text/markdown')
        assert_equal(res.body.decode(), wiki_version.content)

    def test_user_cannot_get_withdrawn_registration_wiki_content(self):
        self._set_up_public_registration_with_wiki_page()
        withdrawal = self.public_registration.retract_registration(user=self.user, save=True)
        token = list(withdrawal.approval_state.values())[0]['approval_token']
        withdrawal.approve_retraction(self.user, token)
        withdrawal.save()
        res = self.app.get(self.public_registration_url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
