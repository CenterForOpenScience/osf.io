from unittest import mock
from datetime import timedelta

from django.utils import timezone

from tests.base import OsfTestCase
from osf_tests.factories import UserFactory
from osf.models.queued_mail import QueuedMail, queue_mail, NO_ADDON, NO_LOGIN_TYPE

from scripts.send_queued_mails import main, pop_and_verify_mails_for_each_user, find_queued_mails_ready_to_be_sent
from website import settings


class TestSendQueuedMails(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = UserFactory()
        self.user.date_last_login = timezone.now()
        self.user.osf_mailing_lists[settings.OSF_HELP_LIST] = True
        self.user.save()

    def queue_mail(self, mail_type=NO_ADDON, user=None, send_at=None):
        return queue_mail(
            to_addr=user.username if user else self.user.username,
            mail=mail_type,
            send_at=send_at or timezone.now(),
            user=user if user else self.user,
            fullname=user.fullname if user else self.user.fullname,
        )

    @mock.patch('osf.models.queued_mail.send_mail')
    def test_queue_addon_mail(self, mock_send):
        self.queue_mail()
        main(dry_run=False)
        assert mock_send.called

    @mock.patch('osf.models.queued_mail.send_mail')
    def test_no_two_emails_to_same_person(self, mock_send):
        user = UserFactory()
        user.osf_mailing_lists[settings.OSF_HELP_LIST] = True
        user.save()
        self.queue_mail(user=user)
        self.queue_mail(user=user)
        main(dry_run=False)
        assert mock_send.call_count == 1

    def test_pop_and_verify_mails_for_each_user(self):
        user_with_email_sent = UserFactory()
        user_with_multiple_emails = UserFactory()
        user_with_no_emails_sent = UserFactory()
        time = timezone.now() - timedelta(days=1)
        mail_sent = QueuedMail(
            user=user_with_email_sent,
            send_at=time,
            to_addr=user_with_email_sent.username,
            email_type=NO_LOGIN_TYPE
        )
        mail_sent.save()
        mail1 = self.queue_mail(user=user_with_email_sent)
        mail2 = self.queue_mail(user=user_with_multiple_emails)
        mail3 = self.queue_mail(user=user_with_multiple_emails)
        mail4 = self.queue_mail(user=user_with_no_emails_sent)
        user_queue = {
            user_with_email_sent._id: [mail1],
            user_with_multiple_emails._id: [mail2, mail3],
            user_with_no_emails_sent._id: [mail4]
        }
        mails_ = list(pop_and_verify_mails_for_each_user(user_queue))
        assert len(mails_) == 2
        user_mails = [mail.user for mail in mails_]
        assert not (user_with_email_sent in user_mails)
        assert user_with_multiple_emails in user_mails
        assert user_with_no_emails_sent in user_mails

    def test_find_queued_mails_ready_to_be_sent(self):
        mail1 = self.queue_mail()
        mail2 = self.queue_mail(send_at=timezone.now()+timedelta(days=1))
        mail3 = self.queue_mail(send_at=timezone.now())
        mails = find_queued_mails_ready_to_be_sent()
        assert mails.count() == 2
