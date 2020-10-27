# -*- coding: utf-8 -*-

from datetime import timedelta

from django.utils import timezone
from nose.tools import *  # noqa

from tests.base import OsfTestCase
from osf.models import NodeLog
from osf_tests.factories import RegistrationFactory, UserFactory

from scripts.embargo_registrations import main


class TestRetractRegistrations(OsfTestCase):

    def setUp(self):
        super(TestRetractRegistrations, self).setUp()
        self.user = UserFactory()
        self.registration = RegistrationFactory(creator=self.user)
        self.registration.embargo_registration(
            self.user,
            timezone.now() + timedelta(days=10)
        )
        self.registration.save()

    def test_new_embargo_should_be_unapproved(self):
        assert_true(self.registration.is_pending_embargo)
        assert_false(self.registration.embargo_end_date)

        main(dry_run=False)
        assert_true(self.registration.is_pending_embargo)
        assert_false(self.registration.embargo_end_date)

    def test_should_not_activate_pending_embargo_less_than_48_hours_old(self):
        self.registration.embargo.initiation_date = timezone.now() - timedelta(hours=47)
        self.registration.embargo.save()
        assert_false(self.registration.embargo_end_date)

        main(dry_run=False)
        self.registration.embargo.refresh_from_db()
        self.registration.refresh_from_db()
        assert_true(self.registration.is_pending_embargo)
        assert_false(self.registration.embargo_end_date)

    def test_should_activate_pending_embargo_that_is_48_hours_old(self):
        self.registration.embargo.initiation_date = timezone.now() - timedelta(hours=48)
        self.registration.embargo.save()
        assert_true(self.registration.is_pending_embargo)
        assert_false(self.registration.embargo_end_date)

        main(dry_run=False)
        self.registration.embargo.refresh_from_db()
        self.registration.refresh_from_db()
        assert_true(self.registration.is_embargoed)
        assert_true(self.registration.embargo_end_date)

    def test_should_activate_pending_embargo_more_than_48_hours_old(self):
        self.registration.embargo.initiation_date = timezone.now() - timedelta(days=365)
        self.registration.embargo.save()
        assert_true(self.registration.is_pending_embargo)
        assert_false(self.registration.embargo_end_date)

        main(dry_run=False)
        self.registration.embargo.refresh_from_db()
        self.registration.refresh_from_db()
        assert_true(self.registration.is_embargoed)
        assert_false(self.registration.is_pending_embargo)
        assert_true(self.registration.embargo_end_date)

    def test_embargo_past_end_date_should_be_completed(self):
        self.registration.embargo.accept()
        assert_true(self.registration.embargo_end_date)
        assert_false(self.registration.is_pending_embargo)

        self.registration.embargo.end_date = timezone.now() - timedelta(days=1)
        self.registration.embargo.save()

        assert_false(self.registration.is_public)
        main(dry_run=False)
        self.registration.embargo.refresh_from_db()
        self.registration.refresh_from_db()
        assert_true(self.registration.is_public)
        assert_false(self.registration.embargo_end_date)
        assert_false(self.registration.is_pending_embargo)
        assert_equal(self.registration.embargo.state, 'completed')

    def test_embargo_before_end_date_should_not_be_completed(self):
        self.registration.embargo.accept()
        assert_true(self.registration.embargo_end_date)
        assert_false(self.registration.is_pending_embargo)

        self.registration.embargo.end_date = timezone.now() + timedelta(days=1)
        self.registration.embargo.save()

        assert_false(self.registration.is_public)
        main(dry_run=False)
        self.registration.embargo.refresh_from_db()
        assert_false(self.registration.is_public)
        assert_true(self.registration.embargo_end_date)
        assert_false(self.registration.is_pending_embargo)

    def test_embargo_approval_adds_to_parent_projects_log(self):
        assert_false(
            self.registration.registered_from.logs.filter(
                action=NodeLog.EMBARGO_APPROVED
            ).exists()
        )

        self.registration.embargo.initiation_date = timezone.now() - timedelta(days=365)
        self.registration.embargo.save()
        main(dry_run=False)

        assert_true(
            self.registration.registered_from.logs.filter(
                action=NodeLog.EMBARGO_APPROVED
            ).exists()
        )

    def test_embargo_completion_adds_to_parent_projects_log(self):
        assert_false(
            self.registration.registered_from.logs.filter(
                action=NodeLog.EMBARGO_COMPLETED
            ).exists()
        )

        self.registration.embargo.accept()
        self.registration.embargo.end_date = timezone.now() - timedelta(days=1)
        self.registration.embargo.save()

        main(dry_run=False)
        assert_true(
            self.registration.registered_from.logs.filter(
                action=NodeLog.EMBARGO_COMPLETED
            ).exists()
        )
