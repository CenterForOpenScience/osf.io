import mock  # noqa
from datetime import datetime, timedelta
from nose.tools import *

from tests.base import OsfTestCase
from tests.factories import UserFactory

from scripts.send_queued_mails import main
from website import mails, settings

class TestSendQueuedMails(OsfTestCase):

    def setUp(self):
        super(TestSendQueuedMails, self).setUp()
        self.user = UserFactory()
        self.user.date_last_login = datetime.utcnow()
        self.user.osf_mailing_lists[settings.OSF_HELP_LIST] = True
        self.user.save()

    def queue_mail(self, mail_type, user=None):
        mails.queue_mail(
            to_addr=self.user.username or user.username,
            mail=mail_type,
            send_at=datetime.utcnow(),
            user=self.user or user,
            fullname=self.user.fullname or user.fullname,
        )

    @mock.patch('website.mails.mails.send_mail')
    def test_queue_addon_mail(self, mock_send):
        self.queue_mail(mails.NO_ADDON)
        main(dry_run=False)
        assert_true(mock_send.called)

    @mock.patch('website.mails.mails.send_mail')
    def test_no_two_emails_to_same_person(self, mock_send):
        user = UserFactory()
        user.osf_mailing_lists[settings.OSF_HELP_LIST] = True
        user.save()
        self.queue_mail(mails.NO_ADDON, user)
        self.queue_mail(mails.NO_ADDON, user)
        main(dry_run=False)
        assert_equal(mock_send.call_count, 1)
