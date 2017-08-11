import pytest

from rest_framework import status

from api.base.settings.defaults import API_BASE

from api_tests.cas.util import fake, make_payload_login_external, add_external_identity_to_user

from osf_tests.factories import UserFactory

# TODO 0: add tests for JWE/JWT failure and malformed request


@pytest.mark.django_db
class TestLoginExternal(object):

    @pytest.fixture()
    def endpoint_url(self):
        return '/{0}cas/login/external/'.format(API_BASE)

    @pytest.fixture()
    def profile_name(self):
        return 'OrcidProfile'

    @pytest.fixture()
    def external_identity_with_provider(self, profile_name):
        return '{}#{}'.format(profile_name, fake.numerify('####-####-####-####'))

    @pytest.fixture()
    def external_identity_with_invalid_provider(self):
        return 'InvalidProfile#{}'.format(fake.numerify('####-####-####-####'))

    @pytest.fixture()
    def malformed_external_identity(self):
        return fake.email()

    @pytest.fixture()
    def user(self):
        return UserFactory()

    # test that user with verified external identity should return 200 with username
    def test_user_with_external_identity_verified(self, app, endpoint_url, user, external_identity_with_provider):

        user = add_external_identity_to_user(user, external_identity_with_provider)
        assert user is not None

        payload = make_payload_login_external(external_identity_with_provider)
        res = app.post(endpoint_url, payload)

        assert res.status_code == status.HTTP_200_OK
        assert res.json.get('username') == user.username

    # test that user with pending (link) external identity should raise 400
    def test_user_with_external_identity_link(self, app, endpoint_url, user, external_identity_with_provider):

        user = add_external_identity_to_user(user, external_identity_with_provider, status='LINK')
        assert user is not None
        payload = make_payload_login_external(external_identity_with_provider)
        res = app.post(endpoint_url, payload, expect_errors=True)

        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40009

    # test that user with pending (create) external identity should raise 400
    def test_user_with_external_identity_create(self, app, endpoint_url, user, external_identity_with_provider):

        user = add_external_identity_to_user(user, external_identity_with_provider, status='CREATE')
        assert user is not None
        payload = make_payload_login_external(external_identity_with_provider)
        res = app.post(endpoint_url, payload, expect_errors=True)

        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40009

    # test that external identity which passes validation but is not found in OSF should raise 400
    def test_account_not_found(self, app, endpoint_url, external_identity_with_provider):

        payload = make_payload_login_external(external_identity_with_provider)
        res = app.post(endpoint_url, payload, expect_errors=True)

        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40009

    # test that external identity with unregistered provider should raise 401
    def test_invalid_external_identity(self, app, endpoint_url, external_identity_with_invalid_provider):

        payload = make_payload_login_external(external_identity_with_invalid_provider)
        res = app.post(endpoint_url, payload, expect_errors=True)

        assert res.status_code == status.HTTP_401_UNAUTHORIZED
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40104

    # test that malformed external identity should raise 401
    def test_malformed_external_identity(self, app, endpoint_url, malformed_external_identity):

        payload = make_payload_login_external(malformed_external_identity)
        res = app.post(endpoint_url, payload, expect_errors=True)

        assert res.status_code == status.HTTP_401_UNAUTHORIZED
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40104
