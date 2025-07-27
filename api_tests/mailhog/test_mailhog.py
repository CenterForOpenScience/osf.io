import requests
import pytest
from django.core.mail import send_mail
from website.mails import TEST
from waffle.testutils import override_switch
from osf import features
from website import settings
from osf_tests.factories import (
    fake_email,
    AuthUserFactory,
)
from tests.base import (
    capture_signals,
    fake
)
from framework import auth
from unittest import mock
from osf.models import OSFUser
from tests.base import (
    OsfTestCase,
)
from website.util import api_url_for


@pytest.mark.django_db
class TestMailHog:

    def test_mailhog_received_mail(self):
        with override_switch(features.ENABLE_MAILHOG, active=True):
            mailhog_v1 = f'{settings.MAILHOG_API_HOST}/api/v1/messages'
            mailhog_v2 = f'{settings.MAILHOG_API_HOST}/api/v2/messages'
            requests.delete(mailhog_v1)

            send_mail('to_addr@mail.com', TEST, name='Mailhog')
            res = requests.get(mailhog_v2).json()
            assert res['count'] == 1
            assert res['items'][0]['Content']['Headers']['To'][0] == 'to_addr@mail.com'
            assert res['items'][0]['Content']['Headers']['Subject'][0] == 'A test email to Mailhog'
            requests.delete(mailhog_v1)


@pytest.mark.django_db
@mock.patch('website.mails.settings.ENABLE_TEST_EMAIL', True)
@mock.patch('website.mails.settings.USE_CELERY', False)
class TestAuthMailhog(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.auth = self.user.auth

    def test_received_confirmation(self):
        url = api_url_for('register_user')
        name, email, password = fake.name(), fake_email(), 'underpressure'
        mailhog_v1 = f'{settings.MAILHOG_API_HOST}/api/v1/messages'
        mailhog_v2 = f'{settings.MAILHOG_API_HOST}/api/v2/messages'
        requests.delete(mailhog_v1)
        with override_switch(features.ENABLE_MAILHOG, active=True):
            with capture_signals() as mock_signals:
                self.app.post(
                    url,
                    json={
                        'fullName': name,
                        'email1': email,
                        'email2': email,
                        'password': password,
                    }
                )
        res = requests.get(mailhog_v2).json()

        assert mock_signals.signals_sent() == {auth.signals.user_registered, auth.signals.unconfirmed_user_created}

        user = OSFUser.objects.get(username=email)
        assert res['total'] == 1
        full_email = f"{res['items'][0]['To'][0]['Mailbox']}@{res['items'][0]['To'][0]['Domain']}"
        assert full_email == user.username
        decoded_body = res['items'][0]['Content']['Body']

        user_token = list(user.email_verifications.keys())[0]
        ideal_link_path = f'/confirm/{user._id}/{user_token}/'
        assert ideal_link_path in decoded_body
