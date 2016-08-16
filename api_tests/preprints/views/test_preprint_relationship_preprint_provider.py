from nose.tools import *

from tests.base import ApiTestCase
from tests.factories import AuthUserFactory, PreprintFactory, PreprintProviderFactory

from api.base.settings.defaults import API_BASE


class TestPreprintRelationshipPreprintProvider(ApiTestCase):
    def setUp(self):
        super(TestPreprintRelationshipPreprintProvider, self).setUp()
        self.user = AuthUserFactory()
        self.preprint = PreprintFactory(creator=self.user, provider=None)
        self.preprint_provider = PreprintProviderFactory()
        self.preprint_preprint_providers_url = '/{0}preprints/{1}/relationships/preprint_provider/'.format(API_BASE, self.preprint._id)

    def create_payload(self, preprint_provider_id):
        return {'data': {'type': 'preprint_providers', 'id': preprint_provider_id}}

    def test_update_preprint_provider(self):
        assert_equal(self.preprint.preprint_provider, None)
        res = self.app.patch_json_api(
            self.preprint_preprint_providers_url,
            self.create_payload(self.preprint_provider._id),
            auth=self.user.auth
        )

        assert_equal(res.status_code, 200)

        # check the relationship
        self.preprint.reload()
        assert_equal(self.preprint.preprint_provider, self.preprint_provider)

    def test_preprint_with_no_permissions(self):
        user = AuthUserFactory()
        user.save()
        res = self.app.patch_json_api(
            self.preprint_preprint_providers_url,
            self.create_payload([self.preprint_provider._id]),
            auth=user.auth,
            expect_errors=True,
        )

        assert_equal(res.status_code, 403)

    def test_change_preprint_provider(self):
        preprint_with_provider = PreprintFactory()
        provider = preprint_with_provider.preprint_provider
        assert_not_equal(provider, self.preprint_provider)
        res = self.app.put_json_api(
            self.preprint_preprint_providers_url,
            self.create_payload(self.preprint_provider._id),
            auth=self.user.auth
        )

        assert_equal(res.status_code, 400)
        assert_equal(self.preprint.preprint_provider, provider)

    def test_get_relationship_information(self):
        res = self.app.get(self.preprint_preprint_providers_url,auth=self.user.auth)

        assert_equal(res.status_code, 200)

    def test_invalid_relationship_type(self):
        invalid_type_payload = self.create_payload(self.preprint_provider._id)
        invalid_type_payload['type'] = 'socks'

        res = self.app.put_json_api(
            self.preprint_preprint_providers_url,
            invalid_type_payload,
            auth=self.user.auth,
            expect_errors=True
        )

        assert_equal(res.status_code, 400)

    def test_invalid_relationship_id(self):
        res = self.app.put_json_api(
            self.preprint_preprint_providers_url,
            self.create_payload('nope nope nope'),
            auth=self.user.auth,
            expect_errors=True
        )

        assert_equal(res.status_code, 400)
