from __future__ import absolute_import
from datetime import datetime

from django.utils import timezone
from nose.tools import *  # noqa PEP8 asserts
from modularodm.exceptions import ValidationError

from framework.auth import Auth

from tests.base import OsfTestCase
from osf_tests.factories import UserFactory, CommentFactory
from website.project.spam.model import SpamStatus


class TestSpamMixin(OsfTestCase):

    def setUp(self):
        super(TestSpamMixin, self).setUp()
        self.comment = CommentFactory()
        self.auth = Auth(user=self.comment.user)

    def test_report_abuse(self):
        user = UserFactory()
        time = timezone.now()
        self.comment.report_abuse(
                user, date=time, category='spam', text='ads', save=True)
        assert_equal(self.comment.spam_status, SpamStatus.FLAGGED)
        equivalent = dict(
            date=time,
            category='spam',
            text='ads',
            retracted=False
        )
        assert_in(user._id, self.comment.reports)
        assert_equal(self.comment.reports[user._id], equivalent)

    def test_report_abuse_own_comment(self):
        with assert_raises(ValueError):
            self.comment.report_abuse(
                self.comment.user,
                category='spam', text='ads',
                save=True
            )
        assert_equal(self.comment.spam_status, SpamStatus.UNKNOWN)

    def test_retract_report(self):
        user = UserFactory()
        time = timezone.now()
        self.comment.report_abuse(
                user, date=time, category='spam', text='ads', save=True
        )
        assert_equal(self.comment.spam_status, SpamStatus.FLAGGED)
        self.comment.retract_report(user, save=True)
        assert_equal(self.comment.spam_status, SpamStatus.UNKNOWN)
        equivalent = {
            'date': time,
            'category': 'spam',
            'text': 'ads',
            'retracted': True
        }
        assert_in(user._id, self.comment.reports)
        assert_equal(self.comment.reports[user._id], equivalent)

    def test_retract_report_not_reporter(self):
        reporter = UserFactory()
        non_reporter = UserFactory()
        self.comment.report_abuse(
                reporter, category='spam', text='ads', save=True
        )
        with assert_raises(ValueError):
            self.comment.retract_report(non_reporter, save=True)
        assert_equal(self.comment.spam_status, SpamStatus.FLAGGED)

    def test_retract_one_report_of_many(self):
        user_1 = UserFactory()
        user_2 = UserFactory()
        time = timezone.now()
        self.comment.report_abuse(
                user_1, date=time, category='spam', text='ads', save=True
        )
        assert_equal(self.comment.spam_status, SpamStatus.FLAGGED)
        self.comment.report_abuse(
                user_2, date=time, category='spam', text='all', save=True
        )
        self.comment.retract_report(user_1, save=True)
        equivalent = {
            'date': time,
            'category': 'spam',
            'text': 'ads',
            'retracted': True
        }
        assert_in(user_1._id, self.comment.reports)
        assert_equal(self.comment.reports[user_1._id], equivalent)
        assert_equal(self.comment.spam_status, SpamStatus.FLAGGED)

    def test_flag_spam(self):
        self.comment.flag_spam()
        self.comment.save()
        assert_equal(self.comment.spam_status, SpamStatus.FLAGGED)

    def test_cannot_remove_flag_not_retracted(self):
        user = UserFactory()
        self.comment.report_abuse(
                user, category='spam', text='ads', save=True
        )
        self.comment.remove_flag(save=True)
        assert_equal(self.comment.spam_status, SpamStatus.FLAGGED)

    def test_remove_flag(self):
        self.comment.flag_spam()
        self.comment.save()
        assert_equal(self.comment.spam_status, SpamStatus.FLAGGED)
        self.comment.remove_flag(save=True)
        assert_equal(self.comment.spam_status, SpamStatus.UNKNOWN)

    def test_confirm_ham(self):
        self.comment.confirm_ham(save=True)
        assert_equal(self.comment.spam_status, SpamStatus.HAM)

    def test_confirm_spam(self):
        self.comment.confirm_spam(save=True)
        assert_equal(self.comment.spam_status, SpamStatus.SPAM)

    def test_validate_reports_bad_key(self):
        self.comment.reports[None] = {'category': 'spam', 'text': 'ads'}
        with assert_raises(ValidationError):
            self.comment.save()

    def test_validate_reports_bad_type(self):
        self.comment.reports[self.comment.user._id] = 'not a dict'
        with assert_raises(ValidationError):
            self.comment.save()

    def test_validate_reports_bad_value(self):
        self.comment.reports[self.comment.user._id] = {'foo': 'bar'}
        with assert_raises(ValidationError):
            self.comment.save()
