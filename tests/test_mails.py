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

    def queue_mail(self, mail, user=None, send_at=None, **kwargs):
        mail = mails.queue_mail(
            to_addr=user.username if user else self.user.username,
            send_at=send_at or datetime.utcnow(),
            user=user or self.user,
            mail=mail,
            fullname=user.fullname if user else self.user.username,
            **kwargs
        )
        return mail

    @mock.patch('website.mails.queued_mails.send_mail')
    def test_no_login_presend_for_active_user(self, mock_mail):
        user = factories.AuthUserFactory()
        mail = self.queue_mail(mail=mails.NO_LOGIN, user=user)
        user.date_last_login = datetime.utcnow() + timedelta(seconds=10)
        user.save()
        assert_false(mail.send_mail())

    @mock.patch('website.mails.queued_mails.send_mail')
    def test_no_login_presend_for_inactive_user(self, mock_mail):
        user = factories.AuthUserFactory()
        mail = self.queue_mail(mail=mails.NO_LOGIN, user=user)
        user.date_last_login = datetime.utcnow() - timedelta(weeks=10)
        user.save()
        assert_true(datetime.utcnow() - timedelta(days=1) > user.date_last_login)
        assert_true(mail.send_mail())

    @mock.patch('website.mails.queued_mails.send_mail')
    def test_no_addon_presend(self, mock_mail):
        mail = self.queue_mail(mail=mails.NO_ADDON)
        assert_true(mail.send_mail())

    @mock.patch('website.mails.queued_mails.send_mail')
    def test_new_public_project_presend_for_no_project(self, mock_mail):
        mail = self.queue_mail(
            mail=mails.NEW_PUBLIC_PROJECT,
            project_title='Oh noes',
            nid='',
        )
        assert_false(mail.send_mail())

    @mock.patch('website.mails.queued_mails.send_mail')
    def test_new_public_project_presend_success(self, mock_mail):
        node = factories.ProjectFactory()
        node.is_public = True
        node.save()
        mail = self.queue_mail(
            mail=mails.NEW_PUBLIC_PROJECT,
            project_title='Oh yass',
            nid=node._id
        )
        assert_true(mail.send_mail())

    @mock.patch('website.mails.queued_mails.send_mail')
    def test_welcome_osf4m_presend(self, mock_mail):
        self.user.date_last_login = datetime.utcnow() - timedelta(days=13)
        self.user.save()
        mail = self.queue_mail(
            mail=mails.WELCOME_OSF4M,
            conference='Buttjamz conference',
            fid=''
        )
        assert_true(mail.send_mail())
        assert_equal(mail.data['downloads'], 0)

    @mock.patch('website.mails.queued_mails.send_mail')
    def test_finding_other_emails_sent_to_user(self, mock_mail):
        user = factories.UserFactory()
        mail = self.queue_mail(
            user=user,
            mail=mails.NO_ADDON,
        )
        assert_equal(len(mail.find_sent_of_same_type_and_user()), 0)
        mail.send_mail()
        assert_equal(len(mail.find_sent_of_same_type_and_user()), 1)

    @mock.patch('website.mails.queued_mails.send_mail')
    def test_user_is_active(self, mock_mail):
        user = factories.UserFactory()
        user.password = 'poo'
        user.is_registered = True
        user.merged_by = None
        user.date_disabled = None
        user.date_confirmed = datetime.utcnow()
        user.save()
        mail = self.queue_mail(
            user=user,
            mail=mails.NO_ADDON,
        )
        assert_true(mail.send_mail())

    @mock.patch('website.mails.queued_mails.send_mail')
    def test_user_is_not_active_no_password(self, mock_mail):
        user = factories.UserFactory()
        user.password = None
        user.save()
        mail = self.queue_mail(
            user=user,
            mail=mails.NO_ADDON,
        )
        assert_false(mail.send_mail())

    @mock.patch('website.mails.queued_mails.send_mail')
    def test_user_is_not_active_not_registered(self, mock_mail):
        user = factories.UserFactory()
        user.is_registered = False
        user.save()
        mail = self.queue_mail(
            user=user,
            mail=mails.NO_ADDON,
        )
        assert_false(mail.send_mail())

    @mock.patch('website.mails.queued_mails.send_mail')
    def test_user_is_not_active_is_merged(self, mock_mail):
        user = factories.UserFactory()
        other_user = factories.UserFactory()
        user.merged_by = other_user
        user.save()
        mail = self.queue_mail(
            user=user,
            mail=mails.NO_ADDON,
        )
        assert_false(mail.send_mail())

    @mock.patch('website.mails.queued_mails.send_mail')
    def test_user_is_not_active_is_disabled(self, mock_mail):
        user = factories.UserFactory()
        user.date_disabled = datetime.utcnow()
        user.save()
        mail = self.queue_mail(
            user=user,
            mail=mails.NO_ADDON,
        )
        assert_false(mail.send_mail())

    @mock.patch('website.mails.queued_mails.send_mail')
    def test_user_is_not_active_is_not_confirmed(self, mock_mail):
        user = factories.UserFactory()
        user.date_confirmed = None
        user.save()
        mail = self.queue_mail(
            user=user,
            mail=mails.NO_ADDON,
        )
        assert_false(mail.send_mail())
