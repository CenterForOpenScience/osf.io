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

    @mock.patch('website.mails.send_mail')
    def test_no_login_callback_for_active_user(self, mock_mail):
        mail = mails.queue_mail(
            to_addr=self.user.username,
            send_at=datetime.utcnow(),
            user=self.user,
            mail=mails.NO_LOGIN,
            fullname=self.user.fullname
        )
        self.user.date_last_login = datetime.utcnow() + timedelta(seconds=10)
        self.user.save()
        assert_false(mail.send_mail())

    @mock.patch('website.mails.send_mail')
    def test_no_login_callback_for_inactive_user(self, mock_mail):
        self.user.date_last_login = datetime.utcnow() - timedelta(weeks=10)
        self.user.save()
        mail = mails.queue_mail(
            to_addr=self.user.username,
            send_at=datetime.utcnow(),
            user=self.user,
            mail=mails.NO_LOGIN,
            fullname=self.user.fullname
        )
        assert_true(mail.send_mail())

    @mock.patch('website.mails.send_mail')
    def test_no_addon_callback(self, mock_mail):
        mail = mails.queue_mail(
            to_addr=self.user.username,
            send_at=datetime.utcnow(),
            user=self.user,
            mail=mails.NO_ADDON,
            fullname=self.user.fullname
        )
        assert_true(mail.send_mail())

    @mock.patch('website.mails.send_mail')
    def test_new_public_project_callback_for_no_project(self, mock_mail):
        mail = mails.queue_mail(
            to_addr=self.user.username,
            send_at=datetime.utcnow(),
            user=self.user,
            mail=mails.NEW_PUBLIC_PROJECT,
            fullname=self.user.fullname,
            project_title='Oh noes',
            nid='',
        )
        assert_false(mail.send_mail())

    @mock.patch('website.mails.send_mail')
    def test_new_public_project_callback_success(self, mock_mail):
        node = factories.ProjectFactory()
        node.is_public = True
        node.save()
        mail = mails.queue_mail(
            to_addr=self.user.username,
            send_at=datetime.utcnow(),
            user=self.user,
            mail=mails.NEW_PUBLIC_PROJECT,
            fullname=self.user.fullname,
            project_title='Oh yass',
            nid=node._id
        )
        assert_true(mail.send_mail())

    @mock.patch('website.mails.send_mail')
    def test_welcome_osf4m_callback(self, mock_mail):
        self.user.date_last_login = datetime.utcnow() - timedelta(days=13)
        self.user.save()
        mail = mails.queue_mail(
            to_addr=self.user.username,
            send_at=datetime.utcnow(),
            user=self.user,
            mail=mails.WELCOME_OSF4M,
            fullname=self.user.fullname,
            conference='Buttjamz conference',
            fid=''
        )
        assert_true(mail.send_mail())
        assert_equal(mail.data['downloads'], 0)

    @mock.patch('website.mails.send_mail')
    def test_finding_other_emails_sent_to_user(self, mock_mail):
        user = factories.UserFactory()
        mail = mails.queue_mail(
            to_addr=user.username,
            send_at=datetime.utcnow(),
            user=user,
            mail=mails.NO_ADDON,
            fullname=user.fullname
        )
        assert_equal(len(mail.find_sent_of_same_type_and_user()), 0)
        mail.send_mail()
        assert_equal(len(mail.find_sent_of_same_type_and_user()), 1)

    @mock.patch('website.mails.send_mail')
    def test_user_is_not_active(self, send_mail):
        user = UserFactory()
        user.is_registered = False
        user.save()
        mail = self.queue_mail(user=user)
        assert_false(mail.send_mail())
