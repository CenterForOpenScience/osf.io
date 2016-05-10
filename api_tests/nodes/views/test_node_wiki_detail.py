from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE
from api_tests.wikis.views.test_wiki_detail import TestWikiDetailMixin
from tests.base import ApiWikiTestCase
from tests.factories import ProjectFactory, RegistrationFactory, NodeWikiFactory


class TestNodeWikiDetailView(ApiWikiTestCase, TestWikiDetailMixin):

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
