import unittest
import smtplib

from unittest import mock
from unittest.mock import MagicMock

import sendgrid
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Category

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

        # Check Mail object arguments
        mock_mail.assert_called_once()
        kwargs = mock_mail.call_args.kwargs
        assert kwargs['from_email'].email == from_addr
        assert kwargs['subject'] == subject
        assert kwargs['html_content'] == message

        mock_mail.return_value.add_personalization.assert_called_once()

        # Capture the categories added via add_category
        # mock_mail.return_value.add_category.assert_called_once()
        assert mock_mail.return_value.add_category.call_count == 2
        added_categories = mock_mail.return_value.add_category.call_args_list
        assert len(added_categories) == 2
        assert isinstance(added_categories[0].args[0], Category)
        assert isinstance(added_categories[1].args[0], Category)
        assert added_categories[0].args[0].get() == category1
        assert added_categories[1].args[0].get() == category2

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

        # Check Mail object arguments
        mock_mail.assert_called_once()
        kwargs = mock_mail.call_args.kwargs
        assert kwargs['from_email'].email == from_addr
        assert kwargs['subject'] == subject
        assert kwargs['html_content'] == message

        mock_client.send.assert_called_once_with(mock_mail.return_value)

        mock_client.send.return_value = mock.Mock(status_code=200, body='correct')
        to_addr = 'not-an-email'
        ret = _send_with_sendgrid(
            from_addr=from_addr,
            to_addr=to_addr,
            subject=subject,
            message=message,
            client=mock_client
        )
        assert not ret
        sentry_mock.assert_called()


if __name__ == '__main__':
    unittest.main()
