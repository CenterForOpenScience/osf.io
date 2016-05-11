from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE

from tests.base import ApiWikiTestCase
from tests.factories import ProjectFactory


class TestWikiContentView(ApiWikiTestCase):

    def _set_up_public_project_with_wiki_page(self):
        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_wiki = self._add_project_wiki_page(self.public_project, self.user)
        self.public_url = '/{}wikis/{}/content/'.format(API_BASE, self.public_wiki._id)

    def _set_up_private_project_with_wiki_page(self):
        self.private_project = ProjectFactory(creator=self.user)
        self.private_wiki = self._add_project_wiki_page(self.private_project, self.user)
        self.private_url = '/{}wikis/{}/content/'.format(API_BASE, self.private_wiki._id)

    def test_logged_out_user_can_get_public_wiki_content(self):
        self._set_up_public_project_with_wiki_page()
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'text/markdown')
        assert_equal(res.body, self.public_wiki.content)

    def test_logged_in_non_contributor_can_get_public_wiki_content(self):
        self._set_up_public_project_with_wiki_page()
        res = self.app.get(self.public_url, auth=self.non_contributor.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'text/markdown')
        assert_equal(res.body, self.public_wiki.content)

    def test_logged_in_contributor_can_get_public_wiki_content(self):
        self._set_up_public_project_with_wiki_page()
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'text/markdown')
        assert_equal(res.body, self.public_wiki.content)

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
        assert_equal(res.body, self.private_wiki.content)
