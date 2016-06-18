# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from nose.tools import *  # noqa

from tests.base import OsfTestCase
from tests.factories import RegistrationFactory
from tests.factories import UserFactory

from scripts.approve_registrations import main


class TestApproveRegistrations(OsfTestCase):

    def setUp(self):
        super(TestApproveRegistrations, self).setUp()
        self.user = UserFactory()
        self.registration = RegistrationFactory(creator=self.user)
        self.registration.is_public = True
        self.registration.require_approval(self.user)

    def test_new_registration_should_not_be_approved(self):
        assert_true(self.registration.is_pending_registration)

        main(dry_run=False)
        assert_false(self.registration.is_registration_approved)

    def test_should_not_approve_pending_registration_less_than_48_hours_old(self):
        # RegistrationApproval#iniation_date is read only
        self.registration.registration_approval._fields['initiation_date'].__set__(
            self.registration.registration_approval,
            (datetime.utcnow() - timedelta(hours=47)),
            safe=True
        )
        self.registration.registration_approval.save()
        assert_false(self.registration.is_registration_approved)

        main(dry_run=False)
        assert_false(self.registration.is_registration_approved)

    def test_should_approve_pending_registration_that_is_48_hours_old(self):
        assert_true(self.registration.registration_approval.pending_approval)  # sanity check
        # RegistrationApproval#iniation_date is read only
        self.registration.registration_approval._fields['initiation_date'].__set__(
            self.registration.registration_approval,
            (datetime.utcnow() - timedelta(hours=48)),
            safe=True
        )
        self.registration.registration_approval.save()
        assert_false(self.registration.is_registration_approved)

        main(dry_run=False)
        assert_true(self.registration.is_registration_approved)
        assert_false(self.registration.registration_approval.pending_approval)

    def test_should_approve_pending_registration_more_than_48_hours_old(self):
        # RegistrationApproval#iniation_date is read only
        self.registration.registration_approval._fields['initiation_date'].__set__(
            self.registration.registration_approval,
            (datetime.utcnow() - timedelta(days=365)),
            safe=True
        )
        self.registration.registration_approval.save()
        assert_false(self.registration.is_registration_approved)

        main(dry_run=False)
        assert_true(self.registration.is_registration_approved)

    def test_registration_adds_to_parent_projects_log(self):
        initial_project_logs = len(self.registration.registered_from.logs)
        # RegistrationApproval#iniation_date is read only
        self.registration.registration_approval._fields['initiation_date'].__set__(
            self.registration.registration_approval,
            (datetime.utcnow() - timedelta(days=365)),
            safe=True
        )
        self.registration.registration_approval.save()
        assert_false(self.registration.is_registration_approved)

        main(dry_run=False)
        assert_true(self.registration.is_registration_approved)
        assert_true(self.registration.is_public)
        # Logs: Created, approval initiated, approval initiated, registered, registration complete
        assert_equal(len(self.registration.registered_from.logs), initial_project_logs + 2)
