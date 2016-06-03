from nose.tools import *  # flake8: noqa
from api.base.settings.defaults import API_BASE

from website.files.models.osfstorage import OsfStorageFile
from website.settings import API_DOMAIN

from tests.base import ApiTestCase
from tests.factories import (AuthUserFactory, ProjectFactory, RegistrationFactory,
                             CommentFactory, NodeWikiFactory, CollectionFactory, PrivateLinkFactory)


class TestGuidRedirect(ApiTestCase):

    def setUp(self):
        super(TestGuidRedirect, self).setUp()
        self.user = AuthUserFactory()

    def _add_private_link(self, project, anonymous=False):
        view_only_link = PrivateLinkFactory(anonymous=anonymous)
        view_only_link.nodes.append(project)
        view_only_link.save()
        return view_only_link

    def test_redirect_to_node_view(self):
        project = ProjectFactory()
        url = '/{}guids/{}/'.format(API_BASE, project._id)
        res = self.app.get(url, auth=self.user.auth)
        redirect_url = '{}{}nodes/{}/'.format(API_DOMAIN, API_BASE, project._id)
        assert_equal(res.status_code, 302)
        assert_equal(res.location, redirect_url)

    def test_redirect_to_registration_view(self):
        registration = RegistrationFactory()
        url = '/{}guids/{}/'.format(API_BASE, registration._id)
        res = self.app.get(url, auth=self.user.auth)
        redirect_url = '{}{}registrations/{}/'.format(API_DOMAIN, API_BASE, registration._id)
        assert_equal(res.status_code, 302)
        assert_equal(res.location, redirect_url)

    def test_redirect_to_collections_view(self):
        collection = CollectionFactory()
        url = '/{}guids/{}/'.format(API_BASE, collection._id)
        res = self.app.get(url, auth=self.user.auth)
        redirect_url = '{}{}collections/{}/'.format(API_DOMAIN, API_BASE, collection._id)
        assert_equal(res.status_code, 302)
        assert_equal(res.location, redirect_url)

    def test_redirect_to_file_view(self):
        test_file = OsfStorageFile.create(
            is_file=True,
            node=ProjectFactory(),
            path='/test',
            name='test',
            materialized_path='/test',
        )
        test_file.save()
        guid = test_file.get_guid(create=True)
        url = '/{}guids/{}/'.format(API_BASE, guid._id)
        res = self.app.get(url, auth=self.user.auth)
        redirect_url = '{}{}files/{}/'.format(API_DOMAIN, API_BASE, test_file._id)
        assert_equal(res.status_code, 302)
        assert_equal(res.location, redirect_url)

    def test_redirect_to_comment_view(self):
        comment = CommentFactory()
        url = '/{}guids/{}/'.format(API_BASE, comment._id)
        res = self.app.get(url, auth=self.user.auth)
        redirect_url = '{}{}comments/{}/'.format(API_DOMAIN, API_BASE, comment._id)
        assert_equal(res.status_code, 302)
        assert_equal(res.location, redirect_url)

    def test_redirect_throws_404_for_invalid_guids(self):
        url = '/{}guids/{}/'.format(API_BASE, 'fakeguid')
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_redirect_when_viewing_private_project_through_view_only_link(self):
        project = ProjectFactory()
        view_only_link = self._add_private_link(project)
        url = '/{}guids/{}/?view_only={}'.format(API_BASE, project._id, view_only_link.key)
        res = self.app.get(url, auth=AuthUserFactory().auth)
        redirect_url = '{}{}nodes/{}/?view_only={}'.format(API_DOMAIN, API_BASE, project._id, view_only_link.key)
        assert_equal(res.status_code, 302)
        assert_equal(res.location, redirect_url)

    def test_redirect_when_viewing_private_project_file_through_view_only_link(self):
        project = ProjectFactory()
        test_file = OsfStorageFile.create(
            is_file=True,
            node=project,
            path='/test',
            name='test',
            materialized_path='/test',
        )
        test_file.save()
        guid = test_file.get_guid(create=True)
        view_only_link = self._add_private_link(project)

        url = '/{}guids/{}/?view_only={}'.format(API_BASE, guid._id, view_only_link.key)
        res = self.app.get(url, auth=AuthUserFactory().auth)
        redirect_url = '{}{}files/{}/?view_only={}'.format(API_DOMAIN, API_BASE, test_file._id, view_only_link.key)
        assert_equal(res.status_code, 302)
        assert_equal(res.location, redirect_url)

    def test_redirect_when_viewing_private_project_comment_through_view_only_link(self):
        project = ProjectFactory()
        view_only_link = self._add_private_link(project)
        comment = CommentFactory(node=project)
        url = '/{}guids/{}/?view_only={}'.format(API_BASE, comment._id, view_only_link.key)
        res = self.app.get(url, auth=AuthUserFactory().auth)
        redirect_url = '{}{}comments/{}/?view_only={}'.format(API_DOMAIN, API_BASE, comment._id, view_only_link.key)
        assert_equal(res.status_code, 302)
        assert_equal(res.location, redirect_url)
