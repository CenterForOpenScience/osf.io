# -*- coding: utf-8 -*-
import unittest
import smtplib

import mock
from nose.tools import *  # flake8: noqa (PEP8 asserts)
import sendgrid

from framework.email.tasks import send_email, _send_with_sendgrid
from website import settings
from tests.base import fake

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
                     "settings.USE_EMAIL is False")
    def test_sending_email(self):
        assert_true(send_email("foo@bar.com", "baz@quux.com", subject='no subject',
                                 message="<h1>Greetings!</h1>", ttls=False, login=False))

    def test_send_with_sendgrid_success(self):
        mock_client = mock.MagicMock()
        mock_client.send.return_value = 200, 'success'
        from_addr, to_addr = fake.email(), fake.email()
        category1, category2 = fake.word(), fake.word()
        subject = fake.bs()
        message = fake.text()
        ret = _send_with_sendgrid(
            from_addr=from_addr,
            to_addr=to_addr,
            subject=subject,
            message=message,
            mimetype='txt',
            client=mock_client,
            categories=(category1, category2)
        )
        assert_true(ret)

        assert_equal(mock_client.send.call_count, 1)
        # First call's argument should be a Mail object with
        # the correct configuration
        first_call_arg = mock_client.send.call_args[0][0]
        assert_is_instance(first_call_arg, sendgrid.Mail)
        assert_equal(first_call_arg.from_email, from_addr)
        assert_equal(first_call_arg.to[0], to_addr)
        assert_equal(first_call_arg.subject, subject)
        assert_equal(first_call_arg.text, message)
        # Categories are set
        assert_equal(first_call_arg.smtpapi.data['category'], (category1, category2))

    def test_send_with_sendgrid_failure_returns_false(self):
        mock_client = mock.MagicMock()
        mock_client.send.return_value = 400, 'failed'
        from_addr, to_addr = fake.email(), fake.email()
        subject = fake.bs()
        message = fake.text()
        ret = _send_with_sendgrid(
            from_addr=from_addr,
            to_addr=to_addr,
            subject=subject,
            message=message,
            mimetype='txt',
            client=mock_client
        )
        assert_false(ret)


if __name__ == '__main__':
    unittest.main()
