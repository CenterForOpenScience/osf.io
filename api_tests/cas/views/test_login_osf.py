import pytest

from rest_framework import status

from api.base.settings.defaults import API_BASE
from api_tests.cas.util import fake, make_payload_login_osf

from framework.auth.core import generate_verification_key

from osf_tests.factories import UserFactory, UnconfirmedUserFactory

# TODO 0: add tests for JWE/JWT failure and malformed request
# TODO 1: add tests for two factor


@pytest.mark.django_db
class TestLoginOSF(object):

    @pytest.fixture()
    def endpoint_url(self):
        return '/{0}cas/login/osf/'.format(API_BASE)

    @pytest.fixture()
    def user(self, password):
        user = UserFactory()
        user.set_password(password)
        user.save()
        return user

    @pytest.fixture()
    def unconfirmed_user(self, password):
        user = UnconfirmedUserFactory()
        user.set_password(password)
        user.save()
        return user

    @pytest.fixture()
    def email(self):
        return fake.email()

    @pytest.fixture()
    def password(self):
        return 'abcdEFGH1234%^&*'

    @pytest.fixture()
    def wrong_password(self):
        return 'abCD12#$'

    @pytest.fixture()
    def verification_key(self, user):
        user.verification_key = generate_verification_key(verification_type=None)
        user.save()
        return user.verification_key

    @pytest.fixture()
    def wrong_verification_key(self):
        return generate_verification_key(verification_type=None)

    @pytest.fixture()
    def remote_authenticated(self):
        return True

    # test that login with correct password should return 200 with user's guid and attributes
    def test_login_existing_user_with_password(self, app, user, endpoint_url, password):

        payload = make_payload_login_osf(user.username, password=password)
        res = app.post(endpoint_url, payload)

        assert res.status_code == status.HTTP_200_OK
        assert res.json.get('userId', '') == user._id
        assert res.json.get('attributes', {}).get('username', '') == user.username

    # test that login with remote principal should return 200 with user's guid and attributes
    def test_login_existing_user_with_remote_principal(self, app, user, endpoint_url, remote_authenticated):

        payload = make_payload_login_osf(user.username, remote_authenticated=remote_authenticated)
        res = app.post(endpoint_url, payload)

        assert res.status_code == status.HTTP_200_OK
        assert res.json.get('userId', '') == user._id
        assert res.json.get('attributes', {}).get('username', '') == user.username

    # test that login with verification key should return 200 with user's guid and attributes
    def test_login_existing_user_with_verification_key(self, app, user, endpoint_url, verification_key):

        payload = make_payload_login_osf(user.username, verification_key=verification_key)
        res = app.post(endpoint_url, payload)

        assert res.status_code == status.HTTP_200_OK
        assert res.json.get('userId', '') == user._id
        assert res.json.get('attributes', {}).get('username', '') == user.username

    # test that login with wrong password should raise 401
    def test_login_existing_user_with_wrong_password(self, app, user, endpoint_url, wrong_password):

        payload = make_payload_login_osf(user.username, password=wrong_password)
        res = app.post(endpoint_url, payload, expect_errors=True)

        assert res.status_code == status.HTTP_401_UNAUTHORIZED
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40102

    # test that login with wrong verification key should raise 401
    def test_login_existing_user_with_wrong_verification_key(self, app, user, endpoint_url, wrong_verification_key):

        payload = make_payload_login_osf(user.username, verification_key=wrong_verification_key)
        res = app.post(endpoint_url, payload, expect_errors=True)

        assert res.status_code == status.HTTP_401_UNAUTHORIZED
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40103

    # test that login with email which is not found in OSF should raise 400
    def test_login_user_not_found(self, app, endpoint_url, email, password):

        payload = make_payload_login_osf(email, password=password)
        res = app.post(endpoint_url, payload, expect_errors=True)

        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40009

    # test that login with an unconfirmed account should raise 400
    def test_login_account_not_confirmed(self, app, endpoint_url, unconfirmed_user, password):

        payload = make_payload_login_osf(unconfirmed_user.username, password=password)
        res = app.post(endpoint_url, payload, expect_errors=True)

        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40010

    # test that login with an unconfirmed account with wrong password should raise 401
    def test_login_account_not_confirmed_with_wrong_password(self, app, endpoint_url, unconfirmed_user, wrong_password):

        payload = make_payload_login_osf(unconfirmed_user.username, password=wrong_password)
        res = app.post(endpoint_url, payload, expect_errors=True)

        assert res.status_code == status.HTTP_401_UNAUTHORIZED
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40102

    # test that login with an disabled account should raise 400
    def test_login_account_disabled(self, app, endpoint_url, user, password):

        user.disable_account()
        user.save()
        user.reload()
        assert user.has_usable_password()
        assert user.has_usable_username()

        payload = make_payload_login_osf(user.username, password=password)
        res = app.post(endpoint_url, payload, expect_errors=True)

        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40012

    # test that login with an disabled account with wrong password should raise 401
    def test_login_account_disabled_with_wrong_password(self, app, endpoint_url, user, wrong_password):

        user.disable_account()
        user.save()
        user.reload()
        assert user.has_usable_password()
        assert user.has_usable_username()

        payload = make_payload_login_osf(user.username, password=wrong_password)
        res = app.post(endpoint_url, payload, expect_errors=True)

        assert res.status_code == status.HTTP_401_UNAUTHORIZED
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40102
