# -*- coding: utf-8 -*-
import mock
from datetime import datetime, timedelta
from nose.tools import *  # PEP 8 sserts

from website import mails, settings
from tests import factories
from tests.base import OsfTestCase

def test_plain_mail():
    mail = mails.Mail('test', subject='A test email to ${name}')
    rendered = mail.text(name='World')
    assert_equal(rendered.strip(), 'Hello World')
    assert_equal(mail.subject(name='World'), 'A test email to World')


def test_html_mail():
    mail = mails.Mail('test', subject='A test email')
    rendered = mail.html(name='World')
    assert_equal(rendered.strip(), 'Hello <p>World</p>')

class TestQueuedMail(OsfTestCase):
    def setUp(self):
        OsfTestCase.setUp(self)
        self.user = factories.AuthUserFactory()
        self.user.is_registered = True
        self.user.save()

    def test_queue_mail(self):
        mail = mails.QueuedMail()
        mail.create(
            to_addr=self.user.username,
            send_at=datetime.utcnow(),
            user=self.user,
            mail=mails.NO_LOGIN,
            fullname=self.user.fullname
        )
        self.user.date_last_login = datetime.utcnow() + timedelta(seconds=10)
        self.user.save()
        assert_equal(mail.send_mail(), False)
        mail = mails.QueuedMail()
        mail.create(
            to_addr=self.user.username,
            send_at=datetime.utcnow(),
            user=self.user,
            mail=mails.NO_ADDON,
            fullname=self.user.fullname
        )
        assert_equal(mail.send_mail(), True)
        self.user.date_last_login = datetime.utcnow() - timedelta(weeks=10)
        self.user.save()
        mail = mails.QueuedMail()
        mail.create(
            to_addr=self.user.username,
            send_at=datetime.utcnow(),
            user=self.user,
            mail=mails.NO_LOGIN,
            fullname=self.user.fullname
        )
        assert_equal(mail.send_mail(), True)
