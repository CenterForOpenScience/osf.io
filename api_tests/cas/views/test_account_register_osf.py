import pytest

from rest_framework import status

from api.base.settings import API_BASE

from api_tests.cas.util import fake, make_request_payload

from framework.auth import signals

from osf.models import OSFUser

from osf_tests.factories import UserFactory

from tests.base import capture_signals

# TODO 1: how to mock methods and check if they are called


@pytest.mark.django_db
class TestAccountRegisterOSF(object):

    @pytest.fixture()
    def endpoint_url(self):
        return '/{0}cas/account/register/osf/'.format(API_BASE)

    @pytest.fixture()
    def new_user(self):
        return {
            'fullname': fake.name(),
            'email': fake.email(),
            'password': fake.password(),
        }

    @pytest.fixture()
    def existing_user(self):
        user = UserFactory()
        return {
            'fullname': user.fullname,
            'email': user.username,
            'password': fake.password(),
        }

    @pytest.fixture()
    def new_user_invalid_email(self):
        return {
            'fullname': fake.name(),
            'email': 'might.be.evil',
            'password': fake.password(),
        }

    @pytest.fixture()
    def new_user_blacklisted_email(self):
        return {
            'fullname': fake.name(),
            'email': 'might.be.evil@mailinator.com',
            'password': fake.password(),
        }

    @pytest.fixture()
    def new_user_invalid_password(self):
        email = fake.email()
        return {
            'fullname': fake.name(),
            'email': email,
            'password': email,
        }

    # test that an unconfirmed new user is created with pending email verifications
    def test_create_new_user(self, app, endpoint_url, new_user):

        assert OSFUser.objects.filter(username=new_user.get('email')).count() == 0

        payload = make_request_payload(new_user)

        with capture_signals() as mock_signals:
            res = app.post(endpoint_url, payload)

        assert res.status_code == status.HTTP_204_NO_CONTENT
        assert mock_signals.signals_sent() == set([signals.unconfirmed_user_created])

        try:
            user = OSFUser.objects.filter(username=new_user.get('email')).get()
        except OSFUser.DoesNotExist:
            user = None

        assert user is not None
        assert not user.is_confirmed
        assert user.get_confirmation_token(user.username) is not None

    # test that user already exists raises 400
    def test_create_new_user_already_exists(self, app, endpoint_url, existing_user):

        payload = make_request_payload(existing_user)
        res = app.post(endpoint_url, payload, expect_errors=True)

        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40004

    # test that invalid email raises 400
    def test_create_new_user_invalid_email(self, app, endpoint_url, new_user_invalid_email):
        assert OSFUser.objects.filter(username=new_user_invalid_email.get('email')).count() == 0

        payload = make_request_payload(new_user_invalid_email)
        res = app.post(endpoint_url, payload, expect_errors=True)

        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40006

    # test that blacked-listed email raises 400
    def test_create_new_user_blacklisted_email(self, app, endpoint_url, new_user_blacklisted_email):
        assert OSFUser.objects.filter(username=new_user_blacklisted_email.get('email')).count() == 0

        payload = make_request_payload(new_user_blacklisted_email)
        res = app.post(endpoint_url, payload, expect_errors=True)

        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40006

    # test that invalid password raises 400
    def test_create_new_user_invalid_password(self, app, endpoint_url, new_user_invalid_password):
        assert OSFUser.objects.filter(username=new_user_invalid_password.get('email')).count() == 0

        payload = make_request_payload(new_user_invalid_password)
        res = app.post(endpoint_url, payload, expect_errors=True)

        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40007
