import mock  # noqa
from datetime import datetime, timedelta
from nose.tools import *

from tests.base import OsfTestCase
from tests.factories import UserFactory

from scripts.triggered_mails import main
from website import mails

class TestTriggeredMails(OsfTestCase):

    def setUp(self):
        super(TestTriggeredMails, self).setUp()
        self.user = UserFactory()
        self.user.date_last_login = datetime.utcnow()
        self.user.save()

    @mock.patch('website.mails.queue_mail')
    def test_dont_trigger_no_login_mail(self, mock_queue):
        self.user.date_last_login = datetime.utcnow() + timedelta(weeks=6)
        self.user.save()
        main(dry_run=False)
        assert_false(mock_queue.called)

    @mock.patch('website.mails.queue_mail')
    def test_trigger_no_login_mail(self, mock_queue):
        self.user.date_last_login = datetime.utcnow() - timedelta(weeks=6)
        self.user.save()
        main(dry_run=False)
        mock_queue.assert_called_once_with(
            user=mock.ANY,
            fullname=self.user.fullname,
            to_addr=self.user.username,
            mail={'callback': mock.ANY, 'template': 'no_login', 'subject': mock.ANY},
            send_at=mock.ANY,
        )
