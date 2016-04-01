from datetime import datetime, timedelta
from nose import tools as nt

from tests.base import OsfTestCase
from tests.factories import CommentFactory, AuthUserFactory
from website.project.model import Comment

from scripts import migrate_spam


class TestMigrateSpam(OsfTestCase):
    def setUp(self):
        super(TestMigrateSpam, self).setUp()
        self.generic_report = {
            'category': 'spam',
            'text': 'spammer spam',
            'date': datetime.utcnow(),
            'retracted': False
        }
        Comment.remove()
        self.user = AuthUserFactory()
        self.comment_1 = CommentFactory()
        self.comment_1.spam_status = 0
        self.comment_1.reports[self.user._id] = self.generic_report
        self.comment_1.save()
        self.comment_2 = CommentFactory()
        self.comment_2.spam_status = 0
        self.comment_2.reports[self.user._id] = self.generic_report
        self.comment_2.save()
        self.comment_3 = CommentFactory()
        self.comment_3.spam_status = 0
        self.comment_3.save()
        self.comment_4 = CommentFactory()
        self.comment_4.date_last_reported = None
        self.comment_4.spam_status = Comment.FLAGGED
        self.comment_4.reports[self.user._id] = self.generic_report
        self.comment_4.save()
        self.comment_5 = CommentFactory()
        self.comment_5.date_last_reported = None
        self.comment_5.spam_status = Comment.UNKNOWN
        self.comment_5.save()
        self.comment_6 = CommentFactory()
        self.comment_6.date_last_reported = None
        self.comment_6.spam_status = Comment.SPAM
        self.comment_6.reports[self.user._id] = self.generic_report
        self.comment_6.save()

    def test_get_status_targets(self):
        targets = migrate_spam.get_no_status_targets()
        nt.assert_equal(len(targets), 3)

    def test_get_latest_targets(self):
        migrate_spam.migrate_status(migrate_spam.get_no_status_targets())
        targets = migrate_spam.get_no_latest_targets()
        nt.assert_equal(len(targets), 4)

    def test_migrate_status(self):
        migrate_spam.migrate_status(migrate_spam.get_no_status_targets())
        self.comment_2.reload()
        self.comment_1.reload()
        self.comment_3.reload()
        nt.assert_equal(self.comment_1.spam_status, Comment.FLAGGED)
        nt.assert_equal(self.comment_2.spam_status, Comment.FLAGGED)
        nt.assert_equal(self.comment_3.spam_status, Comment.UNKNOWN)

    def test_migrate_latest(self):
        migrate_spam.migrate_status(migrate_spam.get_no_status_targets())
        migrate_spam.migrate_latest(migrate_spam.get_no_latest_targets())
        date = self.generic_report['date']
        self.comment_4.reload()
        self.comment_6.reload()
        nt.assert_almost_equal(
            self.comment_4.date_last_reported, date,
            delta=timedelta(microseconds=1000)
        )
        nt.assert_almost_equal(
            self.comment_6.date_last_reported, date,
            delta=timedelta(microseconds=1000)
        )
