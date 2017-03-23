from nose.tools import *  # flake8: noqa

from website.project.metadata.schemas import ACTIVE_META_SCHEMAS
from website.project.model import ensure_schemas

from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase
from osf.models import MetaSchema
from osf_tests.factories import (
    AuthUserFactory
)
from website.project.metadata.schemas import ACTIVE_META_SCHEMAS, LATEST_SCHEMA_VERSION


class TestMetaSchemaList(ApiTestCase):
    def setUp(self):
        super(TestMetaSchemaList, self).setUp()
        self.user = AuthUserFactory()
        ensure_schemas()
        self.url = '/{}metaschemas/'.format(API_BASE)

    def test_pass_authenticated_user_can_view_schemas(self):
        res = self.app.get(self.url, auth=self.user.auth)
        assert_equal(res.status_code, 200)

    def test_cannot_update_metaschemas(self):
        res = self.app.put_json_api(self.url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 405)

    def test_cannot_post_metaschemas(self):
        res = self.app.post_json_api(self.url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 405)

    def test_schemas_are_active(self):
        res = self.app.get(self.url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        for schema in res.json['data']:
            assert_in(schema['attributes']['name'], ACTIVE_META_SCHEMAS)
            assert_equal(schema['attributes']['schema_version'], 2)

    def test_pass_unauthenticated_user_can_view_schemas(self):
        res = self.app.get(self.url)
        assert_equal(res.status_code, 200)

class TestMetaSchemaListFiltering(ApiTestCase):

    def setUp(self):
        super(TestMetaSchemaListFiltering, self).setUp()
        ensure_schemas()
        self.url = '/{}metaschemas/?version=2.1&filter[{}]={}'
        self.registration_schemas_count = MetaSchema.objects.filter(
            category='registration',
            schema_version=LATEST_SCHEMA_VERSION,
            name__in=ACTIVE_META_SCHEMAS
        ).count()
        self.preprintprovider_schemas_count = MetaSchema.objects.filter(category='preprintprovider').count()

    def test_filter_by_category_registration(self):
        res = self.app.get(self.url.format(API_BASE, 'category', 'registration'))
        assert_equal(res.status_code, 200)
        assert_equal(res.json['meta']['total'], self.registration_schemas_count)

    def test_filter_by_category_preprintprovider(self):
        res = self.app.get(self.url.format(API_BASE, 'category', 'preprintprovider'))
        assert_equal(res.status_code, 200)
        assert_equal(res.json['meta']['total'], self.preprintprovider_schemas_count)

    def test_filter_by_category_null(self):
        res = self.app.get(self.url.format(API_BASE, 'category', 'null'))
        assert_equal(res.status_code, 200)
        assert_equal(res.json['meta']['total'], 0)

    def test_invalid_filter(self):
        res = self.app.get(self.url.format(API_BASE, 'fake', 'fake'), expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['source']['parameter'], 'filter')
