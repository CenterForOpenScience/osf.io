from nose.tools import *  # flake8: noqa
from api.base.settings.defaults import API_BASE

from website.files.models.osfstorage import OsfStorageFile
from website.settings import API_DOMAIN

from tests.base import ApiTestCase
from tests.factories import AuthUserFactory, ProjectFactory, RegistrationFactory, CommentFactory, NodeWikiFactory, CollectionFactory


class TestGuidRedirect(ApiTestCase):

    def setUp(self):
        super(TestGuidRedirect, self).setUp()
        self.user = AuthUserFactory()

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

    def test_redirect_throws_501_for_non_implemented_views(self):
        wiki = NodeWikiFactory()
        url = '/{}guids/{}/'.format(API_BASE, wiki._id)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 501)
