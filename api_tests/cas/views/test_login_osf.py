import pytest

from rest_framework import status

from api.base.settings.defaults import API_BASE
from api_tests.cas import util as cas_test_util

from framework.auth.core import generate_verification_key

from osf_tests.factories import UserFactory


@pytest.mark.django_db
class TestLoginOSF(object):

    @pytest.fixture()
    def user(self, new_password):
        user = UserFactory()
        user.set_password(new_password)
        user.save()
        return user

    @pytest.fixture()
    def new_password(self):
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

    @pytest.fixture()
    def endpoint_url(self):
        return '/{0}cas/login/osf/'.format(API_BASE)

    def test_login_existing_user_with_password(self, app, user, endpoint_url, new_password):

        payload = cas_test_util.make_payload_login_osf(user.username, password=new_password)
        res = app.post(endpoint_url, payload)

        assert res.status_code == status.HTTP_200_OK

    def test_login_existing_user_with_remote_principal(self, app, user, endpoint_url, remote_authenticated):

        payload = cas_test_util.make_payload_login_osf(user.username, remote_authenticated=remote_authenticated)
        res = app.post(endpoint_url, payload)

        assert res.status_code == status.HTTP_200_OK

    def test_login_existing_user_with_verification_key(self, app, user, endpoint_url, verification_key):

        payload = cas_test_util.make_payload_login_osf(user.username, verification_key=verification_key)
        res = app.post(endpoint_url, payload)

        assert res.status_code == status.HTTP_200_OK

    def test_login_existing_user_with_wrong_password(self, app, user, endpoint_url, wrong_password):

        payload = cas_test_util.make_payload_login_osf(user.username, password=wrong_password)
        res = app.post(endpoint_url, payload, expect_errors=True)

        assert res.status_code == status.HTTP_401_UNAUTHORIZED
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40102

    def test_login_existing_user_with_wrong_verification_key(self, app, user, endpoint_url, wrong_verification_key):

        payload = cas_test_util.make_payload_login_osf(user.username, verification_key=wrong_verification_key)
        res = app.post(endpoint_url, payload, expect_errors=True)

        assert res.status_code == status.HTTP_401_UNAUTHORIZED
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40103
