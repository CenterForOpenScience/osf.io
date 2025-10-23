import requests
import pytest
from website.mails import send_mail, TEST
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
from conftest import start_mock_send_grid


@pytest.mark.django_db
@pytest.mark.usefixtures('mock_send_grid')
class TestMailHog:

    def test_mailhog_recived_mail(self, mock_send_grid):
        with override_switch(features.ENABLE_MAILHOG, active=True):
            mailhog_v1 = f'{settings.MAILHOG_API_HOST}/api/v1/messages'
            mailhog_v2 = f'{settings.MAILHOG_API_HOST}/api/v2/messages'
            requests.delete(mailhog_v1)

            send_mail('to_addr@mail.com', TEST, name='Mailhog')
            res = requests.get(mailhog_v2).json()
            assert res['count'] == 1
            assert res['items'][0]['Content']['Headers']['To'][0] == 'to_addr@mail.com'
            assert res['items'][0]['Content']['Headers']['Subject'][0] == 'A test email to Mailhog'
            mock_send_grid.assert_called()
            requests.delete(mailhog_v1)


@pytest.mark.django_db
@mock.patch('website.mails.settings.USE_EMAIL', True)
@mock.patch('website.mails.settings.USE_CELERY', False)
class TestAuthMailhog(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.auth = self.user.auth

        self.mock_send_grid = start_mock_send_grid(self)

    def test_recived_confirmation(self):
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
        assert self.mock_send_grid.called

        user = OSFUser.objects.get(username=email)
        user_token = list(user.email_verifications.keys())[0]
        ideal_link_path = f'/confirm/{user._id}/{user_token}/'

        assert ideal_link_path in res['items'][0]['Content']['Body']
