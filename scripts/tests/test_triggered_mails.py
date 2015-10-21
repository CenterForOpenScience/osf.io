import mock
from datetime import datetime, timedelta
from nose.tools import * # noqa

from tests.base import OsfTestCase
from tests.factories import UserFactory

from scripts.triggered_mails import main, find_inactive_users_with_no_inactivity_email_sent_or_queued
from website import mails

class TestTriggeredMails(OsfTestCase):

    def setUp(self):
        super(TestTriggeredMails, self).setUp()
        self.user = UserFactory()
        self.user.date_last_login = datetime.utcnow()
        self.user.save()

    @mock.patch('website.mails.queue_mail')
    def test_dont_trigger_no_login_mail(self, mock_queue):
        self.user.date_last_login = datetime.utcnow() - timedelta(seconds=6)
        self.user.save()
        main(dry_run=False)
        assert_false(mock_queue.called)

    @mock.patch('website.mails.queue_mail')
    def test_trigger_no_login_mail(self, mock_queue):
        self.user.date_last_login = datetime.utcnow() - timedelta(weeks=6)
        self.user.save()
        main(dry_run=False)
        mock_queue.assert_called_with(
            user=mock.ANY,
            fullname=self.user.fullname,
            to_addr=self.user.username,
            mail={'callback': mock.ANY, 'template': 'no_login', 'subject': mock.ANY},
            send_at=mock.ANY,
        )

    @mock.patch('website.mails.send_mail')
    def test_find_inactive_users_with_no_inactivity_email_sent_or_queued(self, mock_mail):
        user_active = UserFactory(fullname='Spot')
        user_inactive = UserFactory(fullname='Nucha')
        user_already_received_mail = UserFactory(fullname='Pep')
        user_active.date_last_login = datetime.utcnow() - timedelta(seconds=6)
        user_inactive.date_last_login = datetime.utcnow() - timedelta(weeks=6)
        user_already_received_mail.date_last_login = datetime.utcnow() - timedelta(weeks=6)
        user_active.save()
        user_inactive.save()
        user_already_received_mail.save()
        mails.queue_mail(to_addr=user_already_received_mail.username,
                         send_at=datetime.utcnow(),
                         user=user_already_received_mail,
                         mail=mails.NO_LOGIN)
        users = find_inactive_users_with_no_inactivity_email_sent_or_queued()
        assert_equal(len(users), 1)
