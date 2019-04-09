import pytest

from api.base import settings
from osf_tests.factories import ProjectFactory, AuthUserFactory
from tests.base import ApiTestCase


@pytest.mark.django_db
class TestNodeCreatorQuota(ApiTestCase):

    def setUp(self):
        super(TestNodeCreatorQuota, self).setUp()
        self.user = AuthUserFactory()
        self.node = ProjectFactory(creator=self.user)
        self.url = '/{}nodes/{}/creator_quota/'.format(settings.API_BASE, self.node._id)

    def test_private_project_authenticated(self):
        res = self.app.get(self.url, auth=self.user.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'

        attributes = res.json['data']['attributes']
        assert attributes['max'] == settings.DEFAULT_MAX_QUOTA * 1024 ** 3
        assert attributes['used'] == 0

    def test_private_project_unauthenticated(self):
        res = self.app.get(self.url, expect_errors=True)

        assert res.status_code == 401
        assert res.content_type == 'application/vnd.api+json'

    def test_public_project(self):
        self.node.is_public = True
        self.node.save()

        res = self.app.get(self.url, auth=self.user.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'

        attributes = res.json['data']['attributes']
        assert attributes['max'] == settings.DEFAULT_MAX_QUOTA * 1024 ** 3
        assert attributes['used'] == 0
