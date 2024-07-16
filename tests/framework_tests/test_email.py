import unittest
import smtplib

from unittest import mock
from unittest.mock import MagicMock

import sendgrid
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Category

from framework.email.tasks import send_email, _send_with_sendgrid
from website import settings
from tests.base import fake
from osf_tests.factories import fake_email

# Check if local mail server is running
SERVER_RUNNING = True
try:
    s = smtplib.SMTP(settings.MAIL_SERVER)
    s.quit()
except Exception as err:
    SERVER_RUNNING = False


class TestEmail(unittest.TestCase):

    @unittest.skipIf(not SERVER_RUNNING,
                     "Mailserver isn't running. Run \"invoke mailserver\".")
    @unittest.skipIf(not settings.USE_EMAIL,
                     'settings.USE_EMAIL is False')
    def test_sending_email(self):
        assert send_email('foo@bar.com', 'baz@quux.com', subject='no subject',
                          message='<h1>Greetings!</h1>', ttls=False, login=False)

    def setUp(self):
        settings.SENDGRID_WHITELIST_MODE = False

    def tearDown(self):
        settings.SENDGRID_WHITELIST_MODE = True

    @mock.patch(f'{_send_with_sendgrid.__module__}.Mail', autospec=True)
    def test_send_with_sendgrid_success(self, mock_mail: MagicMock):
        mock_client = mock.MagicMock(autospec=SendGridAPIClient)
        mock_client.send.return_value = mock.Mock(status_code=200, body='success')
        from_addr, to_addr = fake_email(), fake_email()
        category1, category2 = fake.word(), fake.word()
        subject = fake.bs()
        message = fake.text()
        ret = _send_with_sendgrid(
            from_addr=from_addr,
            to_addr=to_addr,
            subject=subject,
            message=message,
            client=mock_client,
            categories=(category1, category2)
        )
        assert ret
        mock_mail.assert_called_once_with(
            from_email=from_addr,
            to_emails=to_addr,
            subject=subject,
            html_content=message,
        )
        assert len(mock_mail.return_value.category) == 2
        assert mock_mail.return_value.category[0].get() == category1
        assert mock_mail.return_value.category[1].get() == category2
        mock_client.send.assert_called_once_with(mock_mail.return_value)


    @mock.patch(f'{_send_with_sendgrid.__module__}.sentry.log_message', autospec=True)
    @mock.patch(f'{_send_with_sendgrid.__module__}.Mail', autospec=True)
    def test_send_with_sendgrid_failure_returns_false(self, mock_mail, sentry_mock):
        mock_client = mock.MagicMock()
        mock_client.send.return_value = mock.Mock(status_code=400, body='failed')
        from_addr, to_addr = fake_email(), fake_email()
        subject = fake.bs()
        message = fake.text()
        ret = _send_with_sendgrid(
            from_addr=from_addr,
            to_addr=to_addr,
            subject=subject,
            message=message,
            client=mock_client
        )
        assert not ret
        sentry_mock.assert_called_once()
        mock_mail.assert_called_once_with(
            from_email=from_addr,
            to_emails=to_addr,
            subject=subject,
            html_content=message,
        )
        mock_client.send.assert_called_once_with(mock_mail.return_value)


if __name__ == '__main__':
    unittest.main()
