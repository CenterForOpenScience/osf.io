# -*- coding: utf-8 -*-
import unittest
import smtplib

from nose.tools import *  # PEP8 asserts

from framework.email.tasks import send_email
from website import settings

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


if __name__ == '__main__':
    unittest.main()
