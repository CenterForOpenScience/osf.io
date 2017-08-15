import pytest

from django.utils import timezone

from rest_framework import status

from api.base.settings import API_BASE

from api_tests.cas.util import fake, make_request_payload

from framework.auth.core import generate_verification_key

from osf_tests.factories import UserFactory

# TODO 0: add tests for JWE/JWT failure and malformed request
# TODO 1: how to mock methods and check if they are called


@pytest.mark.django_db
class TestAccountPasswordForgot(object):

    @pytest.fixture()
    def endpoint_url(self):
        return '/{0}cas/account/password/forgot/'.format(API_BASE)

    @pytest.fixture()
    def user(self):
        return UserFactory()

    @pytest.fixture()
    def user_credentials(self, user):
        return {
            'email': user.username,
        }

    # test that password reset email is successfully sent and user updated
    def test_send_password_reset_email(self, app, endpoint_url, user, user_credentials):

        assert user.verification_key_v2 == {}
        assert user.email_last_sent is None

        payload = make_request_payload(user_credentials)
        res = app.post(endpoint_url, payload)
        user.reload()

        assert res.status_code == status.HTTP_204_NO_CONTENT
        assert user.verification_key_v2 is not None
        assert user.email_last_sent is not None

    # test that account not found raises 400
    def test_account_not_found(self, app, endpoint_url, user_credentials):

        user_credentials.update({'email': fake.email()})
        payload = make_request_payload(user_credentials)
        res = app.post(endpoint_url, payload, expect_errors=True)

        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40009

    # test that account not eligible raises 400
    def test_account_not_eligible(self, app, endpoint_url, user, user_credentials):

        user.disable_account()
        user.save()
        payload = make_request_payload(user_credentials)
        res = app.post(endpoint_url, payload, expect_errors=True)

        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40008

    # test that active throttle raises 400
    def test_email_throttle_active(self, app, endpoint_url, user, user_credentials):

        user.email_last_sent = timezone.now() + timezone.timedelta(seconds=5)
        user.save()
        payload = make_request_payload(user_credentials)
        res = app.post(endpoint_url, payload, expect_errors=True)

        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40018


@pytest.mark.django_db
class TestAccountPasswordReset(object):

    @pytest.fixture()
    def endpoint_url(self):
        return '/{0}cas/account/password/reset/'.format(API_BASE)

    @pytest.fixture()
    def user_password_pending(self):
        user = UserFactory()
        user.verification_key_v2 = generate_verification_key(verification_type='password')
        user.save()
        return user

    @pytest.fixture()
    def user_credentials(self, user_password_pending):
        verification_code = user_password_pending.verification_key_v2.get('token')
        return {
            'email': user_password_pending.username,
            'verificationCode': verification_code,
            'password': fake.password(),
        }

    # test that password is successfully reset, user updated and expected response is sent back to CAS
    def test_reset_password(self, app, endpoint_url, user_password_pending, user_credentials):

        payload = make_request_payload(user_credentials)
        res = app.post(endpoint_url, payload)
        user_password_pending.reload()
        updated_user = user_password_pending

        assert updated_user.verification_key_v2 == {}
        assert updated_user.verification_key is not None

        expected_response = {
            'verificationKey': updated_user.verification_key,
            'userId': updated_user._id,
            'username': updated_user.username,
            'casAction': 'account-password-reset',
            'nextUrl': False,
        }
        assert res.status_code == status.HTTP_200_OK
        assert res.json == expected_response

    # test that account not found raises 400
    def test_account_not_found(self, app, endpoint_url, user_credentials):

        user_credentials.update({'email': fake.email()})
        payload = make_request_payload(user_credentials)

        res = app.post(endpoint_url, payload, expect_errors=True)

        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40009

    # test that invalid verification code raises 400
    def test_invalid_verification_code(self, app, endpoint_url, user_credentials):

        user_credentials.update({'verificationCode': generate_verification_key(verification_type=None)})
        payload = make_request_payload(user_credentials)

        res = app.post(endpoint_url, payload, expect_errors=True)

        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40016

    # test that invalid password (password that is the same with user's email) raises 400
    def test_invalid_password(self, app, endpoint_url, user_credentials):

        user_credentials.update({'password': user_credentials.get('email')})
        payload = make_request_payload(user_credentials)

        res = app.post(endpoint_url, payload, expect_errors=True)

        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40007
