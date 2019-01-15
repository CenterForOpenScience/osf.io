# Ported from tests.test_mails
import datetime as dt


import pytest
import mock
from django.utils import timezone
from waffle.testutils import override_switch
from website.prereg.utils import get_prereg_schema

from .factories import UserFactory, NodeFactory, DraftRegistrationFactory

from osf.features import DISABLE_ENGAGEMENT_EMAILS
from osf.models.queued_mail import (
    queue_mail, WELCOME_OSF4M,
    NO_LOGIN, NO_ADDON, NEW_PUBLIC_PROJECT
)
from website.mails import mails
from website.settings import DOMAIN

@pytest.fixture()
def user():
    return UserFactory(is_registered=True)

@pytest.mark.django_db
class TestQueuedMail:

    @pytest.fixture()
    def prereg(self, user):
        return DraftRegistrationFactory(initiator=user, registration_schema=get_prereg_schema())

    def queue_mail(self, mail, user, send_at=None, **kwargs):
        mail = queue_mail(
            to_addr=user.username if user else user.username,
            send_at=send_at or timezone.now(),
            user=user,
            mail=mail,
            fullname=user.fullname if user else user.username,
            **kwargs
        )
        return mail

    @mock.patch('osf.models.queued_mail.send_mail')
    def test_no_login_presend_for_active_user(self, mock_mail, user):
        mail = self.queue_mail(mail=NO_LOGIN, user=user)
        user.date_last_login = timezone.now() + dt.timedelta(seconds=10)
        user.save()
        assert mail.send_mail() is False

    @mock.patch('osf.models.queued_mail.send_mail')
    def test_no_login_presend_for_inactive_user(self, mock_mail, user):
        mail = self.queue_mail(mail=NO_LOGIN, user=user)
        user.date_last_login = timezone.now() - dt.timedelta(weeks=10)
        user.save()
        assert timezone.now() - dt.timedelta(days=1) > user.date_last_login
        assert bool(mail.send_mail()) is True

    @mock.patch('osf.models.queued_mail.send_mail')
    def test_no_addon_presend(self, mock_mail, user):
        mail = self.queue_mail(mail=NO_ADDON, user=user)
        assert mail.send_mail() is True

    @mock.patch('osf.models.queued_mail.send_mail')
    def test_new_public_project_presend_for_no_project(self, mock_mail, user):
        mail = self.queue_mail(
            mail=NEW_PUBLIC_PROJECT,
            user=user,
            project_title='Oh noes',
            nid='',
        )
        assert bool(mail.send_mail()) is False

    @mock.patch('osf.models.queued_mail.send_mail')
    def test_new_public_project_presend_success(self, mock_mail, user):
        node = NodeFactory(is_public=True)
        mail = self.queue_mail(
            mail=NEW_PUBLIC_PROJECT,
            user=user,
            project_title='Oh yass',
            nid=node._id
        )
        assert bool(mail.send_mail()) is True

    @mock.patch('osf.models.queued_mail.send_mail')
    def test_welcome_osf4m_presend(self, mock_mail, user):
        user.date_last_login = timezone.now() - dt.timedelta(days=13)
        user.save()
        mail = self.queue_mail(
            mail=WELCOME_OSF4M,
            user=user,
            conference='Buttjamz conference',
            fid='',
            domain=DOMAIN
        )
        assert bool(mail.send_mail()) is True
        assert mail.data['downloads'] == 0

    @mock.patch('osf.models.queued_mail.send_mail')
    def test_finding_other_emails_sent_to_user(self, mock_mail, user):
        mail = self.queue_mail(
            user=user,
            mail=NO_ADDON,
        )
        assert len(mail.find_sent_of_same_type_and_user()) == 0
        mail.send_mail()
        assert len(mail.find_sent_of_same_type_and_user()) == 1

    @mock.patch('osf.models.queued_mail.send_mail')
    def test_user_is_active(self, mock_mail, user):
        mail = self.queue_mail(
            user=user,
            mail=NO_ADDON,
        )
        assert bool(mail.send_mail()) is True

    @mock.patch('osf.models.queued_mail.send_mail')
    def test_user_is_not_active_no_password(self, mock_mail):
        user = UserFactory.build()
        user.set_unusable_password()
        user.save()
        mail = self.queue_mail(
            user=user,
            mail=NO_ADDON,
        )
        assert mail.send_mail() is False

    @mock.patch('osf.models.queued_mail.send_mail')
    def test_user_is_not_active_not_registered(self, mock_mail):
        user = UserFactory(is_registered=False)
        mail = self.queue_mail(
            user=user,
            mail=NO_ADDON,
        )
        assert mail.send_mail() is False

    @mock.patch('osf.models.queued_mail.send_mail')
    def test_user_is_not_active_is_merged(self, mock_mail):
        other_user = UserFactory()
        user = UserFactory(merged_by=other_user)
        mail = self.queue_mail(
            user=user,
            mail=NO_ADDON,
        )
        assert mail.send_mail() is False

    @mock.patch('osf.models.queued_mail.send_mail')
    def test_user_is_not_active_is_disabled(self, mock_mail):
        user = UserFactory(date_disabled=timezone.now())
        mail = self.queue_mail(
            user=user,
            mail=NO_ADDON,
        )
        assert mail.send_mail() is False

    @mock.patch('osf.models.queued_mail.send_mail')
    def test_user_is_not_active_is_not_confirmed(self, mock_mail):
        user = UserFactory(date_confirmed=None)
        mail = self.queue_mail(
            user=user,
            mail=NO_ADDON,
        )
        assert mail.send_mail() is False

    def test_disabled_queued_emails_not_sent_if_switch_active(self, user):
        with override_switch(DISABLE_ENGAGEMENT_EMAILS, active=True):
            assert self.queue_mail(mail=NO_ADDON, user=user) is False
            assert self.queue_mail(mail=NO_LOGIN, user=user) is False
            assert self.queue_mail(mail=WELCOME_OSF4M, user=user) is False
            assert self.queue_mail(mail=NEW_PUBLIC_PROJECT, user=user) is False

    def test_disabled_triggered_emails_not_sent_if_switch_active(self):
        with override_switch(DISABLE_ENGAGEMENT_EMAILS, active=True):
            assert mails.send_mail(to_addr='', mail=mails.WELCOME) is False
            assert mails.send_mail(to_addr='', mail=mails.WELCOME_OSF4I) is False
