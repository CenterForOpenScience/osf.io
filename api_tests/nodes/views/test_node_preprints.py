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

class TestPreprintsListFiltering(PreprintsListFilteringMixin, ApiTestCase):

    def _setUp(self):
        self.user = AuthUserFactory()
        self.provider = PreprintProviderFactory(name='Sockarxiv')
        self.provider_two = PreprintProviderFactory(name='Dockarxiv')
        self.provider_three = PreprintProviderFactory(name='Mockarxiv')

        self.subject = SubjectFactory()
        self.subject_two = SubjectFactory()

        self.preprint = PreprintFactory(creator=self.user, provider=self.provider, subjects=[[self.subject._id]])
        self.preprint_two = PreprintFactory(creator=self.user, project=self.preprint.node, filename='tough.txt', provider=self.provider_two, subjects=[[self.subject_two._id]])

        self.preprint_two.date_created = '2013-12-11 10:09:08.070605+00:00'
        self.preprint_two.date_published = '2013-12-11 10:09:08.070605+00:00'
        self.preprint_two.save()

        self.preprint_three = PreprintFactory(creator=self.user, project=self.preprint.node, filename='darn.txt', provider=self.provider_three, subjects=[[self.subject._id], [self.subject_two._id]])
        self.preprint_three.date_created = '2013-12-11 10:09:08.070605+00:00'
        self.preprint_three.date_published = '2013-12-11 10:09:08.070605+00:00'
        self.preprint_three.is_published = False
        self.preprint_three.save()

        self.url = '/{}nodes/{}/preprints/?version=2.2&'.format(API_BASE, self.preprint.node._id)

    def test_provider_filter_equals_returns_multiple(self):
        pass
