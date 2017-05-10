from nose.tools import *  # flake8: noqa

from website.project.metadata.schemas import LATEST_SCHEMA_VERSION
from website.project.model import ensure_schemas, MetaSchema, Q

from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase
from osf_tests.factories import (
    AuthUserFactory
)
class TestMetaSchemaDetail(ApiTestCase):
    def setUp(self):
        super(TestMetaSchemaDetail, self).setUp()
        self.user = AuthUserFactory()
        ensure_schemas()
        self.schema = MetaSchema.find_one(Q('name', 'eq', 'Prereg Challenge') & Q('schema_version', 'eq', LATEST_SCHEMA_VERSION))
        self.url = '/{}metaschemas/{}/'.format(API_BASE, self.schema._id)

    def test_pass_authenticated_user_can_retrieve_schema(self):
        res = self.app.get(self.url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        data = res.json['data']['attributes']
        assert_equal(data['name'], 'Prereg Challenge')
        assert_equal(data['schema_version'], 2)
        assert_true(data['active'])
        assert_equal(res.json['data']['id'], self.schema._id)

    def test_pass_unauthenticated_user_can_view_schemas(self):
        res = self.app.get(self.url)
        assert_equal(res.status_code, 200)

    def test_inactive_metaschema_returned(self):
        inactive_schema = MetaSchema.objects.get(name='Election Research Preacceptance Competition', active=False)
        url = '/{}metaschemas/{}/'.format(API_BASE, inactive_schema._id)
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['name'], 'Election Research Preacceptance Competition')
        assert_equal(res.json['data']['attributes']['active'], False)

    def test_non_latest_version_metaschema_returned(self):
        old_schema = MetaSchema.objects.get(name='OSF-Standard Pre-Data Collection Registration', schema_version=1)
        url = '/{}metaschemas/{}/'.format(API_BASE, old_schema._id)
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['name'], 'OSF-Standard Pre-Data Collection Registration')
        assert_equal(res.json['data']['attributes']['schema_version'], 1)

    def test_invalid_metaschema_not_found(self):
        self.url = '/{}metaschemas/garbage/'.format(API_BASE)
        res = self.app.get(self.url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
