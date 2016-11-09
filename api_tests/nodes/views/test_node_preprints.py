from nose.tools import *  # flake8: noqa

from framework.auth.core import Auth
from tests.base import ApiTestCase
from api.base.settings.defaults import API_BASE

from website.files.models.osfstorage import OsfStorageFile
from tests.factories import PreprintFactory, AuthUserFactory, ProjectFactory, SubjectFactory
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
