from unittest import mock

import pytest
from waffle.testutils import override_switch
from osf import features
from osf_tests.factories import (
    fake_email,
    AuthUserFactory,
)
from tests.base import (
    capture_signals,
    fake
)
from framework import auth
from osf.models import OSFUser, NotificationType
from tests.base import (
    OsfTestCase,
)
from website.util import api_url_for
from tests.utils import get_mailhog_messages, delete_mailhog_messages


@pytest.mark.django_db
class TestMailHog:

    @override_switch(features.ENABLE_MAILHOG, active=True)
    @mock.patch('website.settings.DEV_MODE', True)
    def test_mailhog_received_mail(self):
        delete_mailhog_messages()

        NotificationType.Type.USER_REGISTRATION_BULK_UPLOAD_FAILURE_ALL.instance.emit(
            message_frequency='instantly',
            destination_address='to_addr@mail.com',
            event_context={
                'user_fullname': '<NAME>',
                'osf_support_email': '<EMAIL>',
                'count': 'test_count',
                'draft_errors': [],
                'error': 'eooer',
            }
        )

        res = get_mailhog_messages()
        assert res['count'] == 1
        assert res['items'][0]['Content']['Headers']['To'][0] == 'to_addr@mail.com'
        assert res['items'][0]['Content']['Headers']['Subject'][0] == NotificationType.objects.get(
            name=NotificationType.Type.USER_REGISTRATION_BULK_UPLOAD_FAILURE_ALL
        ).subject
        delete_mailhog_messages()


@pytest.mark.django_db
class TestAuthMailhog(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.auth = self.user.auth

    @override_switch(features.ENABLE_MAILHOG, active=True)
    def test_received_confirmation(self):
        url = api_url_for('register_user')
        name, email, password = fake.name(), fake_email(), 'underpressure'
        delete_mailhog_messages()
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
        res = get_mailhog_messages()

        assert mock_signals.signals_sent() == {auth.signals.user_registered, auth.signals.unconfirmed_user_created}

        user = OSFUser.objects.get(username=email)
        assert res['total'] == 1
        full_email = f"{res['items'][0]['To'][0]['Mailbox']}@{res['items'][0]['To'][0]['Domain']}"
        assert full_email == user.username
        decoded_body = res['items'][0]['Content']['Body']

        user_token = list(user.email_verifications.keys())[0]
        ideal_link_path = f'/confirm/{user._id}/{user_token}/'
        assert ideal_link_path in decoded_body
        delete_mailhog_messages()
