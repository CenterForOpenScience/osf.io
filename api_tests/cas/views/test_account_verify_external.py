import pytest

from rest_framework import status

from api.base.settings import API_BASE

from api_tests.cas.util import fake, make_request_payload_verify

from framework.auth import signals
from framework.auth.core import generate_verification_key

from osf_tests.factories import UnconfirmedUserFactory, UserFactory

from tests.base import capture_signals


@pytest.mark.django_db
class TestAccountVerifyExternal(object):

    @pytest.fixture()
    def endpoint_url(self):
        return '/{0}cas/account/verify/external/'.format(API_BASE)

    @pytest.fixture()
    def user(self, external_id_provider, external_id):
        user = UserFactory()
        user.external_identity = {
            external_id_provider : {
                external_id: 'LINK'
            }
        }
        user.add_unconfirmed_email(user.username, external_identity=user.external_identity)
        user.save()
        return user

    @pytest.fixture()
    def unconfirmed_user(self, external_id_provider, external_id):
        user = UnconfirmedUserFactory()
        user.external_identity = {
            external_id_provider: {
                external_id: 'CREATE'
            }
        }
        user.add_unconfirmed_email(user.username, external_identity=user.external_identity)
        user.save()
        return user

    @pytest.fixture()
    def external_id_provider(self):
        return "ORCID"

    @pytest.fixture()
    def external_id(self):
        return fake.numerify('####-####-####-####')

    # test that verifying the external identity on a new account should return 200 and update user
    def test_verify_external_new_user_create(self, app, endpoint_url, unconfirmed_user, external_id_provider, external_id):

        payload = make_request_payload_verify(unconfirmed_user, email=None, code=None)
        with capture_signals() as mock_signals:
            res = app.post(endpoint_url, payload)
        unconfirmed_user.reload()
        confirmed_user = unconfirmed_user
        assert res.status_code == status.HTTP_200_OK
        expected_response = {
            'verificationKey': confirmed_user.verification_key,
            'userId': confirmed_user._id,
            'username': confirmed_user.username,
            'createdOrLinked': 'CREATE',
            'casAction': 'account-verify-external',
            'nextUrl': True,
        }
        assert res.json == expected_response

        assert mock_signals.signals_sent() == set([signals.user_confirmed])
        assert confirmed_user.is_confirmed
        assert confirmed_user.external_identity.get(external_id_provider).get(external_id) == 'VERIFIED'
        assert confirmed_user.email_verifications.get('verification_code', None) is None
        assert confirmed_user.verification_key is not None

    # test that verifying the external identity on an existing account should return 200 and update user
    def test_verify_external_existing_user_link(self, app, endpoint_url, user, external_id_provider, external_id):

        payload = make_request_payload_verify(user, email=None, code=None)
        res = app.post(endpoint_url, payload)
        user.reload()
        assert res.status_code == status.HTTP_200_OK
        expected_response = {
            'verificationKey': user.verification_key,
            'userId': user._id,
            'username': user.username,
            'createdOrLinked': 'LINK',
            'casAction': 'account-verify-external',
            'nextUrl': True,
        }
        assert res.json == expected_response
        assert user.external_identity.get(external_id_provider).get(external_id) == 'VERIFIED'
        assert user.email_verifications.get('verification_code', None) is None
        assert user.verification_key is not None

    # test that trying to verify a non-existing email should raise 400(09)
    def test_account_not_found(self, app, endpoint_url, unconfirmed_user):

        email = fake.email()
        code = generate_verification_key(verification_type=None)
        payload = make_request_payload_verify(unconfirmed_user, email=email, code=code)
        res = app.post(endpoint_url, payload, expect_errors=True)
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40009

    # test that trying to verify an external identity with invalid verification code should raise 400(16)
    def test_invalid_verification_code(self, app, endpoint_url, unconfirmed_user):

        unconfirmed_user.save()
        code = generate_verification_key(verification_type=None)
        payload = make_request_payload_verify(unconfirmed_user, email=None, code=code)
        res = app.post(endpoint_url, payload, expect_errors=True)
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40016

    # test that trying to verify a claimed external identity should raise 400(15)
    def test_external_identity_already_claimed(self, app, endpoint_url, user, unconfirmed_user, external_id, external_id_provider):

        user.external_identity[external_id_provider][external_id] = 'VERIFIED'
        user.save()
        payload = make_request_payload_verify(unconfirmed_user, email=None, code=None)
        res = app.post(endpoint_url, payload, expect_errors=True)

        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40015
