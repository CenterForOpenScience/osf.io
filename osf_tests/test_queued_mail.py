# Ported from tests.test_mails
import datetime as dt

import pytest
import mock
from django.utils import timezone

from .factories import UserFactory, NodeFactory

from osf.models.queued_mail import queue_mail
from website import mails

@pytest.fixture()
def user():
    # TODO: Remove date_registered after migration is complete
    return UserFactory(is_registered=True, date_registered=timezone.now())

@pytest.mark.django_db
class TestQueuedMail:

    def queue_mail(self, mail, user, send_at=None, **kwargs):
        mail = queue_mail(
            to_addr=user.username if user else self.user.username,
            send_at=send_at or timezone.now(),
            user=user,
            mail=mail,
            fullname=user.fullname if user else self.user.username,
            **kwargs
        )
        return mail

    @mock.patch('osf.models.queued_mail.send_mail')
    def test_no_login_presend_for_active_user(self, mock_mail, user):
        mail = self.queue_mail(mail=mails.NO_LOGIN, user=user)
        user.date_last_login = timezone.now() + dt.timedelta(seconds=10)
        user.save()
        assert mail.send_mail() is False

    @mock.patch('osf.models.queued_mail.send_mail')
    def test_no_login_presend_for_inactive_user(self, mock_mail, user):
        mail = self.queue_mail(mail=mails.NO_LOGIN, user=user)
        user.date_last_login = timezone.now() - dt.timedelta(weeks=10)
        user.save()
        assert timezone.now() - dt.timedelta(days=1) > user.date_last_login
        assert bool(mail.send_mail()) is True

    @mock.patch('osf.models.queued_mail.send_mail')
    def test_no_addon_presend(self, mock_mail, user):
        mail = self.queue_mail(mail=mails.NO_ADDON, user=user)
        assert mail.send_mail() is True

    @mock.patch('osf.models.queued_mail.send_mail')
    def test_new_public_project_presend_for_no_project(self, mock_mail, user):
        mail = self.queue_mail(
            mail=mails.NEW_PUBLIC_PROJECT,
            user=user,
            project_title='Oh noes',
            nid='',
        )
        assert bool(mail.send_mail()) is False

    @mock.patch('osf.models.queued_mail.send_mail')
    def test_new_public_project_presend_success(self, mock_mail, user):
        node = NodeFactory(is_public=True)
        mail = self.queue_mail(
            mail=mails.NEW_PUBLIC_PROJECT,
            user=user,
            project_title='Oh yass',
            nid=node._id
        )
        assert bool(mail.send_mail()) is True

    # TODO: Uncomment when FileNodeModel is implemented
    # @mock.patch('osf.models.queued_mail.send_mail')
    # def test_welcome_osf4m_presend(self, mock_mail, user):
    #     user.date_last_login = timezone.now() - dt.timedelta(days=13)
    #     user.save()
    #     mail = self.queue_mail(
    #         mail=mails.WELCOME_OSF4M,
    #         user=user,
    #         conference='Buttjamz conference',
    #         fid=''
    #     )
    #     assert bool(mail.send_mail()) is True
    #     assert mail.data['downloads'] == 0

    @mock.patch('osf.models.queued_mail.send_mail')
    def test_finding_other_emails_sent_to_user(self, mock_mail, user):
        mail = self.queue_mail(
            user=user,
            mail=mails.NO_ADDON,
        )
        assert len(mail.find_sent_of_same_type_and_user()) == 0
        mail.send_mail()
        assert len(mail.find_sent_of_same_type_and_user()) == 1

    @mock.patch('osf.models.queued_mail.send_mail')
    def test_user_is_active(self, mock_mail, user):
        mail = self.queue_mail(
            user=user,
            mail=mails.NO_ADDON,
        )
        assert bool(mail.send_mail()) is True

    @mock.patch('osf.models.queued_mail.send_mail')
    def test_user_is_not_active_no_password(self, mock_mail):
        user = UserFactory.build()
        user.set_unusable_password()
        user.save()
        mail = self.queue_mail(
            user=user,
            mail=mails.NO_ADDON,
        )
        assert mail.send_mail() is False

    @mock.patch('osf.models.queued_mail.send_mail')
    def test_user_is_not_active_not_registered(self, mock_mail):
        user = UserFactory(is_registered=False)
        mail = self.queue_mail(
            user=user,
            mail=mails.NO_ADDON,
        )
        assert mail.send_mail() is False

    @mock.patch('osf.models.queued_mail.send_mail')
    def test_user_is_not_active_is_merged(self, mock_mail):
        other_user = UserFactory()
        user = UserFactory(merged_by=other_user)
        mail = self.queue_mail(
            user=user,
            mail=mails.NO_ADDON,
        )
        assert mail.send_mail() is False

    @mock.patch('osf.models.queued_mail.send_mail')
    def test_user_is_not_active_is_disabled(self, mock_mail):
        user = UserFactory(date_disabled=timezone.now())
        mail = self.queue_mail(
            user=user,
            mail=mails.NO_ADDON,
        )
        assert mail.send_mail() is False

    @mock.patch('osf.models.queued_mail.send_mail')
    def test_user_is_not_active_is_not_confirmed(self, mock_mail):
        user = UserFactory(date_confirmed=None)
        mail = self.queue_mail(
            user=user,
            mail=mails.NO_ADDON,
        )
        assert mail.send_mail() is False
