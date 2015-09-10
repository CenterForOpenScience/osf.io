from datetime import datetime, timedelta
from nose.tools import *

from modularodm import Q

from tests.base import OsfTestCase
from tests.factories import UserFactory

from scripts.triggered_mails import main
from website import mails

class TestSendQueuedMails(OsfTestCase):

    def setUp(self):
        super(TestSendQueuedMails, self).setUp()
        self.user = UserFactory()
        self.user.date_last_login = datetime.utcnow()
        self.user.save()

    def test_emails_to_different_people(self):
        queued_emails = list(mails.QueuedMail.find(
            Q('sent_at', 'ne', None)
        ))
        user1 = UserFactory()
        user2 = UserFactory()
        mails.queue_mail(to_addr=user1.username, mail=mails.NO_ADDON, send_at=datetime.utcnow(), user=user1, fullname=user1.fullname)
        mails.queue_mail(to_addr=user2.username, mail=mails.NO_ADDON, send_at=datetime.utcnow(), user=user2, fullname=user2.fullname)
        main(dry_run=False)
        queued_emails_new = set(mails.QueuedMail.find(
            Q('sent_at', 'ne', None)
        )) - set(queued_emails)
        assert_equal(len(queued_emails_new), 2)

    def test_no_two_emails_to_same_person(self):
        user = UserFactory()
        mails.queue_mail(to_addr=user.username, mail=mails.NO_ADDON, send_at=datetime.utcnow(), user=user, fullname=user.fullname)
        mails.queue_mail(to_addr=user.username, mail=mails.NO_ADDON, send_at=datetime.utcnow(), user=user, fullname=user.fullname)
        main(dry_run=False)
        queued_emails = list(mails.QueuedMail.find(
            Q('user', 'eq', user) &
            Q('sent_at', 'ne', None)
        ))
        assert_equal(len(queued_emails), 1)
