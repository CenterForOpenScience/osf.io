import pytest

from rest_framework import status

from api.base.settings import API_BASE

from api_tests.cas.util import fake, make_request_payload

from framework.auth import signals
from framework.auth.core import generate_verification_key

from osf_tests.factories import UnconfirmedUserFactory

from tests.base import capture_signals


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

    def test_verify_and_register_new_user(self, app, endpoint_url, unconfirmed_user, user_credentials):

        payload = make_request_payload(user_credentials)

        with capture_signals() as mock_signals:
            res = app.post(endpoint_url, payload)

        assert res.status_code == status.HTTP_200_OK
        assert mock_signals.signals_sent() == set([signals.user_confirmed])

        unconfirmed_user.reload()
        confirmed_user = unconfirmed_user
        assert confirmed_user.is_confirmed
        assert confirmed_user.verification_key is not None

        expected_response = {
            'verificationKey': confirmed_user.verification_key,
            'userId': confirmed_user._id,
            'username': confirmed_user.username,
            'casAction': 'account-verify-osf',
            'nextUrl': False,
        }
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


@pytest.mark.django_db
class TestAccountVerifyExternal(object):

    def test_register_new_user_create(self):
        pass

    def test_register_existing_user_link(self):
        pass
