import pytest

from rest_framework import status

from api.base.settings import API_BASE

from api_tests.cas.util import fake, make_request_payload

from framework.auth import signals

from osf.models import OSFUser

from osf_tests.factories import UserFactory

from tests.base import capture_signals


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

    def test_create_new_user(self, app, endpoint_url, new_user):

        assert OSFUser.objects.filter(username=new_user.get('email')).count() == 0

        payload = make_request_payload(new_user)

        with capture_signals() as mock_signals:
            res = app.post(endpoint_url, payload)

        assert res.status_code == status.HTTP_204_NO_CONTENT
        assert mock_signals.signals_sent() == set([signals.unconfirmed_user_created])

        assert OSFUser.objects.filter(username=new_user.get('email')).count() == 1

    def test_create_new_user_already_exists(self, app, endpoint_url, existing_user):

        assert OSFUser.objects.filter(username=existing_user.get('email')).count() == 1

        payload = make_request_payload(existing_user)
        with capture_signals() as mock_signals:
            res = app.post(endpoint_url, payload, expect_errors=True)
            assert len(mock_signals.signals_sent()) == 0

        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40004

    def test_create_new_user_invalid_email(self, app, endpoint_url, new_user_invalid_email):
        assert OSFUser.objects.filter(username=new_user_invalid_email.get('email')).count() == 0

        payload = make_request_payload(new_user_invalid_email)
        with capture_signals() as mock_signals:
            res = app.post(endpoint_url, payload, expect_errors=True)

        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40006
        assert len(mock_signals.signals_sent()) == 0

    def test_create_new_user_blacklisted_email(self, app, endpoint_url, new_user_blacklisted_email):
        assert OSFUser.objects.filter(username=new_user_blacklisted_email.get('email')).count() == 0

        payload = make_request_payload(new_user_blacklisted_email)
        with capture_signals() as mock_signals:
            res = app.post(endpoint_url, payload, expect_errors=True)

        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40006
        assert len(mock_signals.signals_sent()) == 0

    def test_create_new_user_invalid_password(self, app, endpoint_url, new_user_invalid_password):
        assert OSFUser.objects.filter(username=new_user_invalid_password.get('email')).count() == 0

        payload = make_request_payload(new_user_invalid_password)
        with capture_signals() as mock_signals:
            res = app.post(endpoint_url, payload, expect_errors=True)

        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40007
        assert len(mock_signals.signals_sent()) == 0


@pytest.mark.django_db
class TestAccountRegisterExternal(object):

    def test_create_new_user(self):
        pass

    def test_link_existing_user(self):
        pass
