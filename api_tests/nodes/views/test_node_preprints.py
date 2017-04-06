from nose.tools import *  # flake8: noqa

from framework.auth.core import Auth
from tests.base import ApiTestCase
from api.base.settings.defaults import API_BASE
from api_tests.preprints.filters.test_filters import PreprintsListFilteringMixin

from website.preprints.model import PreprintService
from website.files.models.osfstorage import OsfStorageFile
from osf_tests.factories import PreprintFactory, AuthUserFactory, ProjectFactory, SubjectFactory, PreprintProviderFactory
from api_tests import utils as test_utils


class TestNodePreprintList(ApiTestCase):
    def setUp(self):
        super(TestNodePreprintList, self).setUp()

        self.user = AuthUserFactory()
        self.auth = Auth(self.user)
        self.preprint = PreprintFactory(creator=self.user, is_published=False)

        self.url = '/{}nodes/{}/preprints/'.format(API_BASE, self.preprint.node._id)

    def test_user_can_see_own_unpublished_preprint(self):
        res = self.app.get(self.url, auth=self.user.auth, expect_errors=True)

        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['id'], self.preprint._id)

    def test_other_user_can_see_unpublished_preprint_on_public_node(self):
        noncontrib = AuthUserFactory()
        self.preprint.node.set_privacy('public')
        res = self.app.get(self.url, auth=noncontrib.auth)

        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['id'], self.preprint._id)

    def test_other_user_cannot_see_unpublished_preprint_on_private_node(self):
        noncontrib = AuthUserFactory()
        res = self.app.get(self.url, auth=noncontrib.auth, expect_errors=True)

        assert_equal(res.status_code, 403)

    def test_user_can_see_own_published_preprint(self):
        self.preprint.set_published(True, auth=self.auth)
        res = self.app.get(self.url, auth=self.user.auth)

        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['id'], self.preprint._id)

    def test_other_user_can_see_published_preprint_on_public_node(self):
        self.preprint.set_published(True, auth=self.auth)
        noncontrib = AuthUserFactory()
        res = self.app.get(self.url, auth=noncontrib.auth)

        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['id'], self.preprint._id)

class TestNodePreprintsListFiltering(PreprintsListFilteringMixin, ApiTestCase):

    def setUp(self):
        self.user = AuthUserFactory()
        # all different providers
        self.provider = PreprintProviderFactory(name='Sockarxiv')
        self.provider_two = PreprintProviderFactory(name='Piratearxiv')
        self.provider_three = PreprintProviderFactory(name='Mockarxiv')
        # all same project
        self.project = ProjectFactory(creator=self.user)
        self.project_two = self.project
        self.project_three = self.project
        self.url = '/{}nodes/{}/preprints/?version=2.2&'.format(API_BASE, self.project._id)
        super(TestNodePreprintsListFiltering, self).setUp()

    def test_provider_filter_equals_returns_one(self):
        expected = [self.preprint_two._id]
        res = self.app.get('{}{}'.format(self.provider_url, self.provider_two._id), auth=self.user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert_equal(expected, actual)
