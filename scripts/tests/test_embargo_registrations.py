# -*- coding: utf-8 -*-

from datetime import date, datetime, timedelta
from nose.tools import *  # noqa

from tests.base import OsfTestCase
from tests.factories import RegistrationFactory
from tests.factories import UserFactory

from scripts.embargo_registrations import main


class TestRetractRegistrations(OsfTestCase):

    def setUp(self):
        super(TestRetractRegistrations, self).setUp()
        self.user = UserFactory()
        self.registration = RegistrationFactory(creator=self.user)
        self.registration.embargo_registration(
            self.user,
            datetime.utcnow() + timedelta(days=10)
        )
        self.registration.save()

    def test_new_embargo_should_be_unapproved(self):
        assert_true(self.registration.pending_embargo)
        assert_false(self.registration.embargo_end_date)

        main(dry_run=False)
        assert_true(self.registration.pending_embargo)
        assert_false(self.registration.embargo_end_date)

    def test_should_not_activate_pending_embargo_less_than_48_hours_old(self):
        # Embargo#iniation_date is read only
        self.registration.embargo._fields['initiation_date'].__set__(
            self.registration.embargo,
            (datetime.utcnow() - timedelta(hours=47)),
            safe=True
        )
        self.registration.embargo.save()
        assert_false(self.registration.embargo_end_date)

        main(dry_run=False)
        assert_false(self.registration.embargo_end_date)

    def test_should_activate_pending_embargo_that_is_48_hours_old(self):
        # Embargo#iniation_date is read only
        self.registration.embargo._fields['initiation_date'].__set__(
            self.registration.embargo,
            (datetime.utcnow() - timedelta(hours=48)),
            safe=True
        )
        self.registration.embargo.save()
        assert_true(self.registration.pending_embargo)
        assert_false(self.registration.embargo_end_date)

        main(dry_run=False)
        assert_false(self.registration.pending_embargo)
        assert_true(self.registration.embargo_end_date)

    def test_should_activate_pending_embargo_more_than_48_hours_old(self):
        # Embargo#iniation_date is read only
        self.registration.embargo._fields['initiation_date'].__set__(
            self.registration.embargo,
            (datetime.utcnow() - timedelta(days=365)),
            safe=True
        )
        self.registration.embargo.save()
        assert_true(self.registration.pending_embargo)
        assert_false(self.registration.embargo_end_date)

        main(dry_run=False)
        assert_false(self.registration.pending_embargo)
        assert_true(self.registration.embargo_end_date)

    def test_embargo_past_end_date_should_be_completed(self):
        approval_token = self.registration.embargo.approval_state[self.user._id]['approval_token']
        self.registration.embargo.approve_embargo(self.user, approval_token)
        self.registration.save()
        assert_true(self.registration.embargo_end_date)
        assert_false(self.registration.pending_embargo)

        # Embargo#iniation_date is read only
        self.registration.embargo._fields['end_date'].__set__(
            self.registration.embargo,
            (datetime.utcnow() - timedelta(days=1)),
            safe=True
        )
        self.registration.embargo.save()

        assert_false(self.registration.is_public)
        main(dry_run=False)
        assert_true(self.registration.is_public)
        assert_false(self.registration.embargo_end_date)
        assert_false(self.registration.pending_embargo)
        assert_equal(self.registration.embargo.state, 'completed')

    def test_embargo_before_end_date_should_not_be_completed(self):
        approval_token = self.registration.embargo.approval_state[self.user._id]['approval_token']
        self.registration.embargo.approve_embargo(self.user, approval_token)
        self.registration.save()
        assert_true(self.registration.embargo_end_date)
        assert_false(self.registration.pending_embargo)

        # Embargo#iniation_date is read only
        self.registration.embargo._fields['end_date'].__set__(
            self.registration.embargo,
            (datetime.utcnow() + timedelta(days=1)),
            safe=True
        )
        self.registration.embargo.save()

        assert_false(self.registration.is_public)
        main(dry_run=False)
        assert_false(self.registration.is_public)
        assert_true(self.registration.embargo_end_date)
        assert_false(self.registration.pending_embargo)

    def test_embargo_approval_adds_to_parent_registrations_log(self):
        initial_num_logs = len(self.registration.logs)
        # Embargo#iniation_date is read only
        self.registration.embargo._fields['initiation_date'].__set__(
            self.registration.embargo,
            (datetime.utcnow() - timedelta(days=365)),
            safe=True
        )
        self.registration.embargo.save()

        main(dry_run=False)
        assert_equal(len(self.registration.logs), initial_num_logs + 1)

    def test_embargo_completion_adds_to_parent_registrations_log(self):
        initial_num_logs = len(self.registration.logs)
        approval_token = self.registration.embargo.approval_state[self.user._id]['approval_token']
        self.registration.embargo.approve_embargo(self.user, approval_token)
        self.registration.save()

        # Embargo#iniation_date is read only
        self.registration.embargo._fields['end_date'].__set__(
            self.registration.embargo,
            (datetime.utcnow() - timedelta(days=1)),
            safe=True
        )
        self.registration.embargo.save()

        main(dry_run=False)
        # Approved embargo, made registration public, and completed embargo
        assert_equal(len(self.registration.logs), initial_num_logs + 3)
