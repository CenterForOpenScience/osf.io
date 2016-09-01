from nose.tools import *

from tests.base import ApiTestCase
from tests.factories import AuthUserFactory, PreprintFactory, PreprintProviderFactory

from api.base.settings.defaults import API_BASE


class TestPreprintRelationshipPreprintProvider(ApiTestCase):
    def setUp(self):
        super(TestPreprintRelationshipPreprintProvider, self).setUp()
        self.user = AuthUserFactory()
        self.read_write_user = AuthUserFactory()

        self.preprint = PreprintFactory(creator=self.user, providers=None)
        self.preprint.add_contributor(self.read_write_user)
        self.preprint.save()

        self.preprint_provider_one = PreprintProviderFactory()
        self.preprint_provider_two = PreprintProviderFactory()

        self.preprint_preprint_providers_url = self.create_url(self.preprint._id)

    def create_url(self, preprint_id):
        return '/{0}preprints/{1}/relationships/preprint_providers/'.format(API_BASE, preprint_id)

    def create_payload(self, *preprint_provider_ids):
        data = []
        for provider_id in preprint_provider_ids:
            data.append({'type': 'preprint_providers', 'id': provider_id})
        return {'data': data}

    def test_add_preprint_providers(self):
        assert_equal(self.preprint.preprint_providers, None)
        res = self.app.post_json_api(
            self.preprint_preprint_providers_url,
            self.create_payload(self.preprint_provider_one._id, self.preprint_provider_two._id),
            auth=self.user.auth
        )

        assert_equal(res.status_code, 201)

        # check the relationship
        self.preprint.reload()
        assert_in(self.preprint_provider_one, self.preprint.preprint_providers)
        assert_in(self.preprint_provider_two, self.preprint.preprint_providers)

    def test_add_preprint_providers_permission_denied(self):
        noncontrib = AuthUserFactory()
        assert_equal(self.preprint.preprint_providers, None)
        res = self.app.post_json_api(
            self.preprint_preprint_providers_url,
            self.create_payload(self.preprint_provider_one._id, self.preprint_provider_two._id),
            auth=noncontrib.auth,
            expect_errors=True
        )

        assert_equal(res.status_code, 403)

    def test_add_through_patch_one_provider_while_removing_other(self):
        self.preprint.preprint_providers = [self.preprint_provider_one]
        self.preprint.save()

        assert_in(self.preprint_provider_one, self.preprint.preprint_providers)
        assert_not_in(self.preprint_provider_two, self.preprint.preprint_providers)

        res = self.app.patch_json_api(
            self.preprint_preprint_providers_url,
            self.create_payload(self.preprint_provider_two._id),
            auth=self.user.auth
        )

        assert_equal(res.status_code, 200)

        self.preprint.reload()
        assert_not_in(self.preprint_provider_one, self.preprint.preprint_providers)
        assert_in(self.preprint_provider_two, self.preprint.preprint_providers)

    def test_add_through_post_to_preprint_with_provider(self):
        self.preprint.preprint_providers = [self.preprint_provider_one]
        self.preprint.save()

        assert_in(self.preprint_provider_one, self.preprint.preprint_providers)
        assert_not_in(self.preprint_provider_two, self.preprint.preprint_providers)

        res = self.app.post_json_api(
            self.preprint_preprint_providers_url,
            self.create_payload(self.preprint_provider_two._id),
            auth=self.user.auth
        )

        assert_equal(res.status_code, 201)

        self.preprint.reload()
        assert_in(self.preprint_provider_one, self.preprint.preprint_providers)
        assert_in(self.preprint_provider_two, self.preprint.preprint_providers)

    def test_add_provider_with_no_permissions(self):
        new_user = AuthUserFactory()
        new_user.save()
        res = self.app.post_json_api(
            self.preprint_preprint_providers_url,
            self.create_payload(self.preprint_provider_one._id),
            auth=new_user.auth,
            expect_errors=True,
        )

        assert_equal(res.status_code, 403)

    def test_delete_nothing(self):
        res = self.app.delete_json_api(
            self.preprint_preprint_providers_url,
            self.create_payload(),
            auth=self.user.auth
        )
        assert_equal(res.status_code, 204)

    def test_remove_providers(self):
        self.preprint.preprint_providers = [self.preprint_provider_one]
        self.preprint.save()

        assert_in(self.preprint_provider_one, self.preprint.preprint_providers)
        res = self.app.put_json_api(
            self.preprint_preprint_providers_url,
            self.create_payload(),
            auth=self.user.auth
        )
        assert_equal(res.status_code, 200)
        self.preprint.reload()
        assert_equal(self.preprint.preprint_providers, [])

    def test_remove_providers_with_no_auth(self):
        res = self.app.put_json_api(
            self.preprint_preprint_providers_url,
            self.create_payload(),
            expect_errors=True
        )
        assert_equal(res.status_code, 401)

    def test_using_post_making_no_changes_returns_204(self):
        self.preprint.preprint_providers = [self.preprint_provider_one]
        self.preprint.save()
        assert_in(self.preprint_provider_one, self.preprint.preprint_providers)

        res = self.app.post_json_api(
            self.preprint_preprint_providers_url,
            self.create_payload(self.preprint_provider_one._id),
            auth=self.user.auth
        )

        assert_equal(res.status_code, 204)
        self.preprint.reload()
        assert_in(self.preprint_provider_one, self.preprint.preprint_providers)

    def test_delete_user_is_admin(self):
        self.preprint.preprint_providers = [self.preprint_provider_one]
        self.preprint.save()
        assert_in(self.preprint_provider_one, self.preprint.preprint_providers)

        res = self.app.delete_json_api(
            self.preprint_preprint_providers_url,
            self.create_payload(self.preprint_provider_one._id),
            auth=self.user.auth
        )

        assert_equal(res.status_code, 204)
        self.preprint.reload()
        assert_not_in(self.preprint_provider_one, self.preprint.preprint_providers)

    def test_delete_provider_user_is_read_write(self):
        self.preprint.preprint_providers = [self.preprint_provider_one]
        self.preprint.save()
        assert_in(self.preprint_provider_one, self.preprint.preprint_providers)

        res = self.app.delete_json_api(
            self.preprint_preprint_providers_url,
            self.create_payload(self.preprint_provider_one._id),
            auth=self.read_write_user.auth,
            expect_errors=True
        )

        assert_equal(res.status_code, 403)
        self.preprint.reload()
        assert_in(self.preprint_provider_one, self.preprint.preprint_providers)

    def test_add_provider_user_is_read_write(self):
        self.preprint.preprint_providers = []
        self.preprint.preprint_providers.append(self.preprint_provider_one)
        self.preprint.save()
        assert_in(self.preprint_provider_one, self.preprint.preprint_providers)

        res = self.app.post_json_api(
            self.preprint_preprint_providers_url,
            self.create_payload(self.preprint_provider_two._id),
            auth=self.read_write_user.auth,
            expect_errors=True
        )

        assert_equal(res.status_code, 403)
        self.preprint.reload()
        assert_in(self.preprint_provider_one, self.preprint.preprint_providers)

    def test_change_provider_user_is_read_write(self):
        self.preprint.preprint_providers = []
        self.preprint.preprint_providers.append(self.preprint_provider_one)
        self.preprint.save()
        assert_in(self.preprint_provider_one, self.preprint.preprint_providers)

        res = self.app.put_json_api(
            self.preprint_preprint_providers_url,
            self.create_payload(self.preprint_provider_two._id),
            auth=self.read_write_user.auth,
            expect_errors=True
        )

        assert_equal(res.status_code, 403)
        self.preprint.reload()
        assert_in(self.preprint_provider_one, self.preprint.preprint_providers)

    def test_get_relationship_information(self):
        res = self.app.get(self.preprint_preprint_providers_url,auth=self.user.auth)

        assert_equal(res.status_code, 200)

    def test_invalid_relationship_type(self):
        invalid_type_payload = self.create_payload(self.preprint_provider_one._id)
        invalid_type_payload['data'][0]['type'] = 'socks'

        res = self.app.put_json_api(
            self.preprint_preprint_providers_url,
            invalid_type_payload,
            auth=self.user.auth,
            expect_errors=True
        )

        assert_equal(res.status_code, 409)

    def test_provider_does_not_exist(self):
        res = self.app.post_json_api(
            self.preprint_preprint_providers_url,
            self.create_payload('nope nope nope'),
            auth=self.user.auth,
            expect_errors=True
        )

        assert_equal(res.status_code, 404)
