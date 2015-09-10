from datetime import datetime, timedelta
from nose.tools import *

from modularodm import Q

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

    def test_trigger_no_login_mail(self):
        main(dry_run=False)
        sent_emails = len(list(mails.QueuedMail.find(
            Q('sent_at', 'ne', None)
        )))
        self.user.date_last_login = datetime.utcnow() - timedelta(weeks=6)
        self.user.save()
        main(dry_run=False)
        queued_emails = list(mails.QueuedMail.find(
            Q('sent_at', 'ne', None)
        ))
        new_emails = len(queued_emails) - sent_emails
        assert_equal(new_emails, 1)
        assert_equal(queued_emails[-1].to_addr, self.user.username)


