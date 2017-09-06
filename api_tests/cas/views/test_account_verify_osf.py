import pytest

from django.utils import timezone

from rest_framework import status

from api.base.settings import API_BASE

from api_tests.cas.util import fake, make_request_payload

from framework.auth import signals
from framework.auth.core import generate_verification_key

from osf.models import OSFUser

from osf_tests.factories import UnconfirmedUserFactory, UserFactory

from tests.base import capture_signals


@pytest.mark.django_db
class TestAccountVerifyOSFResend(object):

    @pytest.fixture()
    def endpoint_url(self):
        return '/{0}cas/account/verify/osf/resend/'.format(API_BASE)

    @pytest.fixture()
    def unconfirmed_user(self):
        return UnconfirmedUserFactory()

    @pytest.fixture()
    def active_user(self):
        return UserFactory()

    @pytest.fixture()
    def email_new_user(self):
        return fake.email()

    # test that resend confirmation sends email and returns 204
    def test_resend_confirmation(self, app, endpoint_url, unconfirmed_user):

        user_credentials = {
            'email': unconfirmed_user.username,
        }
        payload = make_request_payload(user_credentials)
        res = app.post(endpoint_url, payload)

        assert res.status_code == status.HTTP_204_NO_CONTENT

    # test that resend confirmation on active user returns 400
    def test_resend_confirmation_on_active_user(self, app, endpoint_url, active_user):

        user_credentials = {
            'email': active_user.username,
        }
        payload = make_request_payload(user_credentials)
        res = app.post(endpoint_url, payload, expect_errors=True)

        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40005

    # test that resend confirmation on non-existing account returns 400
    def test_resend_confirmation_on_account_not_found(self, app, endpoint_url, email_new_user):

        assert OSFUser.objects.filter(username=email_new_user).count() == 0

        user_credentials = {
            'email': email_new_user,
        }
        payload = make_request_payload(user_credentials)
        res = app.post(endpoint_url, payload, expect_errors=True)

        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40009

    # test that resend confirmation on account not eligible raises 400
    def test_account_not_eligible(self, app, endpoint_url, active_user):

        active_user.disable_account()
        active_user.save()
        user_credentials = {
            'email': active_user.username,
        }
        payload = make_request_payload(user_credentials)
        res = app.post(endpoint_url, payload, expect_errors=True)

        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40008

    # test that resend confirmation on account with an active throttle raises 400
    def test_email_throttle_active(self, app, endpoint_url, unconfirmed_user):

        unconfirmed_user.email_last_sent = timezone.now() + timezone.timedelta(seconds=5)
        unconfirmed_user.save()
        user_credentials = {
            'email': unconfirmed_user.username,
        }
        payload = make_request_payload(user_credentials)
        res = app.post(endpoint_url, payload, expect_errors=True)

        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40018


@pytest.mark.django_db
class TestAccountVerifyOSF(object):

    @pytest.fixture()
    def endpoint_url(self):
        return '/{0}cas/account/verify/osf/'.format(API_BASE)

    @pytest.fixture()
    def unconfirmed_user(self):
        return UnconfirmedUserFactory()

    @pytest.fixture()
    def user_credentials(self, unconfirmed_user):
        verification_code = unconfirmed_user.get_confirmation_token(unconfirmed_user.username, force=True, renew=True)
        unconfirmed_user.save()
        return {
            'email': unconfirmed_user.username,
            'verificationCode': verification_code
        }

    # test that new user confirmation verifies email, registers user and returns expected response to CAS
    def test_verify_and_register_new_user(self, app, endpoint_url, unconfirmed_user, user_credentials):

        payload = make_request_payload(user_credentials)
        with capture_signals() as mock_signals:
            res = app.post(endpoint_url, payload)
        unconfirmed_user.reload()
        confirmed_user = unconfirmed_user
        expected_response = {
            'verificationKey': confirmed_user.verification_key,
            'userId': confirmed_user._id,
            'username': confirmed_user.username,
            'casAction': 'account-verify-osf',
            'nextUrl': False,
        }

        assert res.status_code == status.HTTP_200_OK
        assert mock_signals.signals_sent() == set([signals.user_confirmed])
        assert confirmed_user.is_confirmed
        assert confirmed_user.verification_key is not None
        assert res.json == expected_response

    def test_account_not_found(self, app, endpoint_url, user_credentials):

        user_credentials.update({'email': fake.email()})
        payload = make_request_payload(user_credentials)

        with capture_signals() as mock_signals:
            res = app.post(endpoint_url, payload, expect_errors=True)

        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40009
        assert len(mock_signals.signals_sent()) == 0

    def test_invalid_verification_code(self, app, endpoint_url, user_credentials):

        user_credentials.update({'verificationCode': generate_verification_key(verification_type=None)})
        payload = make_request_payload(user_credentials)

        with capture_signals() as mock_signals:
            res = app.post(endpoint_url, payload, expect_errors=True)

        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40016
        assert len(mock_signals.signals_sent()) == 0

    def test_email_already_confirmed(self, app, endpoint_url, unconfirmed_user, user_credentials):

        unconfirmed_user.register(unconfirmed_user.username)
        unconfirmed_user.save()

        payload = make_request_payload(user_credentials)

        with capture_signals() as mock_signals:
            res = app.post(endpoint_url, payload, expect_errors=True)

        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40005
        assert len(mock_signals.signals_sent()) == 0
